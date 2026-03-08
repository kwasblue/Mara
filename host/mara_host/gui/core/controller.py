# mara_host/gui/core/controller.py
"""
Robot controller for GUI operations.

Bridges the async services layer with the Qt GUI thread.
Runs on a dedicated asyncio thread and emits Qt signals
for thread-safe UI updates.
"""

import asyncio
import threading
from typing import Optional, Callable, Any

from mara_host.gui.core.signals import GuiSignals
from mara_host.gui.core.state import AppState, ConnectionState, TransportConfig, DeviceCapabilities


class RobotController:
    """
    Async robot controller for GUI operations.

    Manages robot connection and provides high-level operations
    that emit Qt signals for UI updates.

    Example:
        signals = GuiSignals()
        controller = RobotController(signals)

        # Start the async event loop
        controller.start()

        # Connect to robot (schedules async operation)
        controller.connect_serial("/dev/cu.usbserial-0001")

        # Perform operations
        controller.arm()
        controller.set_velocity(0.5, 0.0)

        # Shutdown
        controller.stop()
    """

    def __init__(self, signals: GuiSignals, dev_mode: bool = False):
        """
        Initialize robot controller.

        Args:
            signals: GuiSignals instance for emitting UI updates
            dev_mode: Enable verbose logging
        """
        self.signals = signals
        self._dev_mode = dev_mode

        # Asyncio event loop (runs in background thread)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

        # Services
        self._connection_service = None
        self._state_service = None
        self._motion_service = None
        self._telemetry_service = None
        self._motor_service = None
        self._servo_service = None
        self._gpio_service = None

        # State
        self._state = AppState()
        self._running = False
        self._disconnecting = False  # Track if disconnect is in progress

    @property
    def state(self) -> AppState:
        """Get current application state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self._state.is_connected

    def _dev_log(self, message: str) -> None:
        """Log a message if in dev mode."""
        if self._dev_mode:
            self.signals.log("DEBUG", message)

    # ==================== Lifecycle ====================

    def start(self) -> None:
        """Start the async event loop in a background thread."""
        if self._running:
            return

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever,
            name="RobotController",
            daemon=True,
        )
        self._loop_thread.start()
        self._running = True

    def stop(self) -> None:
        """Stop the controller and cleanup."""
        if not self._running:
            return

        # Schedule disconnect and WAIT for it to complete
        if self._connection_service:
            try:
                future = self._schedule(self._disconnect_async())
                # Wait for disconnect to complete (with timeout)
                future.result(timeout=3.0)
            except Exception:
                pass  # Best effort - don't block shutdown

        # Cancel all pending tasks and stop the event loop
        if self._loop:
            # Schedule cleanup on the event loop
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._cleanup_tasks(), self._loop
                )
                future.result(timeout=2.0)
            except Exception:
                pass

            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread:
            self._loop_thread.join(timeout=2.0)

        self._running = False

    async def _cleanup_tasks(self) -> None:
        """Cancel all pending tasks on the event loop."""
        tasks = [
            t for t in asyncio.all_tasks(self._loop)
            if t is not asyncio.current_task()
        ]

        for task in tasks:
            task.cancel()

        # Wait for all tasks to complete cancellation
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _schedule(self, coro) -> asyncio.Future:
        """Schedule a coroutine on the async thread."""
        if not self._loop or not self._running:
            raise RuntimeError("Controller not started")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ==================== Connection ====================

    def connect_serial(self, port: str, baudrate: int = 115200) -> None:
        """
        Connect via serial transport.

        Args:
            port: Serial port path
            baudrate: Baud rate
        """
        config = TransportConfig(
            transport_type="serial",
            port=port,
            baudrate=baudrate,
        )
        self._schedule(self._connect_async(config))

    def connect_tcp(self, host: str, port: int = 3333) -> None:
        """
        Connect via TCP transport.

        Args:
            host: TCP host address
            port: TCP port
        """
        config = TransportConfig(
            transport_type="tcp",
            host=host,
            tcp_port=port,
        )
        self._schedule(self._connect_async(config))

    def disconnect(self) -> None:
        """Disconnect from robot."""
        self._schedule(self._disconnect_async())

    async def _connect_async(self, config: TransportConfig) -> None:
        """Internal async connection."""
        import asyncio
        from mara_host.services.transport import (
            ConnectionService,
            ConnectionConfig,
            TransportType,
        )
        from mara_host.services.control import (
            StateService,
            MotionService,
            MotorService,
            ServoService,
            GpioService,
        )
        from mara_host.services.telemetry import TelemetryService

        # Wait for any pending disconnect to complete
        for _ in range(30):  # Max 3 seconds
            if not self._disconnecting:
                break
            await asyncio.sleep(0.1)

        # If still disconnecting, force cleanup
        if self._disconnecting:
            self.signals.log_warning("Previous disconnect still in progress, forcing cleanup")
            self._disconnecting = False

        self._state.connection_state = ConnectionState.CONNECTING
        self._state.transport_config = config
        self.signals.status_message.emit("Connecting...")

        try:
            # Create connection config
            transport_type = TransportType.SERIAL
            if config.transport_type == "tcp":
                transport_type = TransportType.TCP

            conn_config = ConnectionConfig(
                transport_type=transport_type,
                port=config.port,
                baudrate=config.baudrate,
                host=config.host,
                tcp_port=config.tcp_port,
            )

            # Connect
            self._dev_log(f"Connecting: {transport_type.value} {config.port or config.host}")
            self._connection_service = ConnectionService(conn_config)
            info = await self._connection_service.connect()
            self._dev_log(f"Connected: protocol={info.protocol_version}, features={info.features}")

            # Initialize services
            client = self._connection_service.client
            self._state_service = StateService(client)
            self._motion_service = MotionService(client)
            self._telemetry_service = TelemetryService(client)
            self._motor_service = MotorService(client)
            self._servo_service = ServoService(client)
            self._gpio_service = GpioService(client)

            # Subscribe to telemetry
            self._telemetry_service.on_state(self._on_state_changed)
            self._telemetry_service.on_imu(self._on_imu_data)
            await self._telemetry_service.start(
                interval_ms=self._state.telemetry_interval_ms
            )

            # Auto-attach servos to default channels for GUI control
            for servo_id in range(2):
                try:
                    await self._servo_service.attach(
                        servo_id=servo_id,
                        channel=servo_id,  # Channel 0 for servo 0, etc.
                        min_us=500,
                        max_us=2500,
                        initial_angle=90,  # Center position
                    )
                except Exception:
                    pass  # Best effort - servo might not be configured

            # Update state
            self._state.connection_state = ConnectionState.CONNECTED
            self._state.firmware_version = info.firmware_version or ""
            self._state.protocol_version = info.protocol_version or 0
            self._state.robot_state = "IDLE"

            # Store device capabilities
            self._state.capabilities = DeviceCapabilities(
                features=info.features or [],
                capabilities_mask=info.capabilities or 0,
            )

            # Emit signals
            self.signals.connection_changed.emit(
                True,
                f"Connected - FW: {info.firmware_version}",
            )
            self.signals.capabilities_changed.emit(self._state.capabilities)
            self.signals.log_info(f"Connected to robot (FW: {info.firmware_version})")
            if self._state.capabilities.features:
                self.signals.log_info(f"Features: {self._state.capabilities.summary()}")

        except Exception as e:
            self._state.connection_state = ConnectionState.ERROR
            self._state.last_error = str(e)
            self.signals.connection_changed.emit(False, "")
            self.signals.connection_error.emit(str(e))
            self.signals.log_error(f"Connection failed: {e}")

    async def _disconnect_async(self) -> None:
        """Internal async disconnect."""
        import asyncio

        self._disconnecting = True
        try:
            # Stop telemetry first
            if self._telemetry_service:
                try:
                    self._telemetry_service.stop()
                except Exception as e:
                    self.signals.log_error(f"Telemetry stop error: {e}")

            # Disconnect from robot
            if self._connection_service:
                try:
                    await self._connection_service.disconnect()
                except Exception as e:
                    self.signals.log_error(f"Connection disconnect error: {e}")

            # Wait for serial port to be fully released
            await asyncio.sleep(0.5)

        except Exception as e:
            self.signals.log_error(f"Disconnect error: {e}")

        finally:
            self._connection_service = None
            self._state_service = None
            self._motion_service = None
            self._telemetry_service = None
            self._motor_service = None
            self._servo_service = None
            self._gpio_service = None

            self._state.connection_state = ConnectionState.DISCONNECTED
            self._state.robot_state = "UNKNOWN"
            self._disconnecting = False
            self.signals.connection_changed.emit(False, "Disconnected")

    # ==================== State Control ====================

    def arm(self) -> None:
        """Arm the robot."""
        self._schedule(self._arm_async())

    def disarm(self) -> None:
        """Disarm the robot."""
        self._schedule(self._disarm_async())

    def activate(self) -> None:
        """Activate the robot."""
        self._schedule(self._activate_async())

    def deactivate(self) -> None:
        """Deactivate the robot."""
        self._schedule(self._deactivate_async())

    def estop(self) -> None:
        """Emergency stop."""
        self._schedule(self._estop_async())

    def clear_estop(self) -> None:
        """Clear emergency stop."""
        self._schedule(self._clear_estop_async())

    async def _arm_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: arm()")
        result = await self._state_service.arm()
        self._dev_log(f"RSP: arm -> ok={result.ok}, error={result.error}")
        if result.ok:
            self.signals.state_changed.emit("ARMED")
            self.signals.log_info("Robot armed")
        else:
            self.signals.status_error.emit(result.error or "Arm failed")

    async def _disarm_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: disarm()")
        result = await self._state_service.disarm()
        self._dev_log(f"RSP: disarm -> ok={result.ok}")
        if result.ok:
            self.signals.state_changed.emit("IDLE")
            self.signals.log_info("Robot disarmed")
        else:
            self.signals.status_error.emit(result.error or "Disarm failed")

    async def _activate_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: activate()")
        result = await self._state_service.activate()
        self._dev_log(f"RSP: activate -> ok={result.ok}")
        if result.ok:
            self.signals.state_changed.emit("ACTIVE")
            self.signals.log_info("Robot activated")
        else:
            self.signals.status_error.emit(result.error or "Activate failed")

    async def _deactivate_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: deactivate()")
        result = await self._state_service.deactivate()
        self._dev_log(f"RSP: deactivate -> ok={result.ok}")
        if result.ok:
            self.signals.state_changed.emit("ARMED")
            self.signals.log_info("Robot deactivated")
        else:
            self.signals.status_error.emit(result.error or "Deactivate failed")

    async def _estop_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: estop()")
        result = await self._state_service.estop()
        self._dev_log(f"RSP: estop -> ok={result.ok}")
        self._state.estop_active = True
        self.signals.state_changed.emit("ESTOP")
        self.signals.log_warning("E-STOP ACTIVATED")

    async def _clear_estop_async(self) -> None:
        if not self._state_service:
            return
        self._dev_log("CMD: clear_estop()")
        result = await self._state_service.clear_estop()
        self._dev_log(f"RSP: clear_estop -> ok={result.ok}")
        if result.ok:
            self._state.estop_active = False
            self.signals.state_changed.emit("IDLE")
            self.signals.log_info("E-STOP cleared")
        else:
            self.signals.status_error.emit(result.error or "Clear E-STOP failed")

    # ==================== Motion Control ====================

    def set_velocity(self, vx: float, omega: float) -> None:
        """Set robot velocity (fire-and-forget)."""
        self._schedule(self._set_velocity_async(vx, omega))

    def stop_motion(self) -> None:
        """Stop all motion."""
        self._schedule(self._stop_motion_async())

    async def _set_velocity_async(self, vx: float, omega: float) -> None:
        if not self._motion_service:
            return
        await self._motion_service.set_velocity(vx, omega)

    async def _stop_motion_async(self) -> None:
        if not self._motion_service:
            return
        await self._motion_service.stop()

    # ==================== Motor Control ====================

    def set_motor_speed(self, motor_id: int, speed: float) -> None:
        """Set DC motor speed."""
        self._schedule(self._set_motor_speed_async(motor_id, speed))

    def stop_motor(self, motor_id: int) -> None:
        """Stop a DC motor."""
        self._schedule(self._stop_motor_async(motor_id))

    async def _set_motor_speed_async(self, motor_id: int, speed: float) -> None:
        if not self._motor_service:
            return
        # Use fast method for smooth slider control (fire-and-forget)
        await self._motor_service.set_speed_fast(motor_id, speed)

    async def _stop_motor_async(self, motor_id: int) -> None:
        if not self._motor_service:
            return
        await self._motor_service.stop(motor_id)

    # ==================== Servo Control ====================

    def set_servo_angle(self, servo_id: int, angle: float) -> None:
        """Set servo angle (fast, fire-and-forget for smooth sliding)."""
        self._schedule(self._set_servo_angle_async(servo_id, angle))

    def set_servo_angle_reliable(self, servo_id: int, angle: float) -> None:
        """Set servo angle with reliable delivery (use on slider release)."""
        self._schedule(self._set_servo_angle_reliable_async(servo_id, angle))

    async def _set_servo_angle_async(self, servo_id: int, angle: float) -> None:
        if not self._servo_service:
            return
        # Use fast method for smooth slider control (fire-and-forget)
        await self._servo_service.set_angle_fast(servo_id, angle)

    async def _set_servo_angle_reliable_async(self, servo_id: int, angle: float) -> None:
        if not self._servo_service:
            return
        # Use reliable method to ensure final position is reached
        await self._servo_service.set_angle(servo_id, angle)

    # ==================== GPIO Control ====================

    def gpio_write(self, channel: int, value: int) -> None:
        """Write GPIO value."""
        self._schedule(self._gpio_write_async(channel, value))

    def gpio_toggle(self, channel: int) -> None:
        """Toggle GPIO channel."""
        self._schedule(self._gpio_toggle_async(channel))

    async def _gpio_write_async(self, channel: int, value: int) -> None:
        if not self._gpio_service:
            return
        await self._gpio_service.write(channel, value)

    async def _gpio_toggle_async(self, channel: int) -> None:
        if not self._gpio_service:
            return
        await self._gpio_service.toggle(channel)

    # ==================== Telemetry Callbacks ====================

    def _on_state_changed(self, state: str) -> None:
        """Handle state change from telemetry."""
        self._state.robot_state = state
        self.signals.state_changed.emit(state)

    def _on_imu_data(self, imu) -> None:
        """Handle IMU data from telemetry."""
        self.signals.imu_data.emit(imu)

    # ==================== Send Command ====================

    def send_command(
        self,
        command: str,
        payload: dict,
        callback: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        """
        Send an arbitrary command.

        Args:
            command: Command name (e.g., "CMD_GPIO_WRITE")
            payload: Command payload
            callback: Optional callback(success, result_or_error)
        """
        self._schedule(self._send_command_async(command, payload, callback))

    async def _send_command_async(
        self,
        command: str,
        payload: dict,
        callback: Optional[Callable[[bool, str], None]],
    ) -> None:
        if not self._connection_service or not self._connection_service.client:
            if callback:
                callback(False, "Not connected")
            return

        client = self._connection_service.client
        self._dev_log(f"CMD: {command} {payload}")
        self.signals.command_sent.emit(command, payload)

        try:
            ok, error = await client.send_reliable(command, payload)
            self._dev_log(f"RSP: {command} -> ok={ok}, error={error}")
            if callback:
                callback(ok, error or "OK")
            self.signals.command_ack.emit(0, ok, error or "OK")
        except Exception as e:
            self._dev_log(f"ERR: {command} -> {e}")
            if callback:
                callback(False, str(e))
            self.signals.command_ack.emit(0, False, str(e))

    # ==================== Motor PID Control ====================

    def enable_velocity_pid(self, motor_id: int, enable: bool) -> None:
        """Enable/disable velocity PID for a motor."""
        self._schedule(self._enable_velocity_pid_async(motor_id, enable))

    def set_velocity_gains(self, motor_id: int, kp: float, ki: float, kd: float) -> None:
        """Set velocity PID gains for a motor."""
        self._schedule(self._set_velocity_gains_async(motor_id, kp, ki, kd))

    def set_velocity_target(self, motor_id: int, omega: float) -> None:
        """Set velocity target for a motor (rad/s)."""
        self._schedule(self._set_velocity_target_async(motor_id, omega))

    async def _enable_velocity_pid_async(self, motor_id: int, enable: bool) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_DC_VEL_PID_ENABLE", {"motor_id": motor_id, "enable": enable})

    async def _set_velocity_gains_async(self, motor_id: int, kp: float, ki: float, kd: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_DC_SET_VEL_GAINS", {"motor_id": motor_id, "kp": kp, "ki": ki, "kd": kd})

    async def _set_velocity_target_async(self, motor_id: int, omega: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_DC_SET_VEL_TARGET", {"motor_id": motor_id, "omega": omega})

    # ==================== Stepper Control ====================

    def stepper_move(self, motor_id: int, steps: int, speed: float) -> None:
        """Move stepper motor by relative steps."""
        self._schedule(self._stepper_move_async(motor_id, steps, speed))

    def stepper_stop(self, motor_id: int) -> None:
        """Stop stepper motor."""
        self._schedule(self._stepper_stop_async(motor_id))

    def stepper_enable(self, motor_id: int, enable: bool) -> None:
        """Enable/disable stepper motor."""
        self._schedule(self._stepper_enable_async(motor_id, enable))

    async def _stepper_move_async(self, motor_id: int, steps: int, speed: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_STEPPER_MOVE_REL", {"motor_id": motor_id, "steps": steps, "speed": speed})

    async def _stepper_stop_async(self, motor_id: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_STEPPER_STOP", {"motor_id": motor_id})

    async def _stepper_enable_async(self, motor_id: int, enable: bool) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_STEPPER_ENABLE", {"motor_id": motor_id, "enable": enable})

    # ==================== Encoder Control ====================

    def encoder_attach(self, encoder_id: int, pin_a: int, pin_b: int) -> None:
        """Attach encoder to pins."""
        self._schedule(self._encoder_attach_async(encoder_id, pin_a, pin_b))

    def encoder_reset(self, encoder_id: int) -> None:
        """Reset encoder count."""
        self._schedule(self._encoder_reset_async(encoder_id))

    def encoder_read(self, encoder_id: int, callback: Optional[Callable[[int], None]] = None) -> None:
        """Read encoder count."""
        self._schedule(self._encoder_read_async(encoder_id, callback))

    async def _encoder_attach_async(self, encoder_id: int, pin_a: int, pin_b: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_ENCODER_ATTACH", {"encoder_id": encoder_id, "pin_a": pin_a, "pin_b": pin_b})

    async def _encoder_reset_async(self, encoder_id: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_ENCODER_RESET", {"encoder_id": encoder_id})

    async def _encoder_read_async(self, encoder_id: int, callback: Optional[Callable[[int], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        ok, error = await client.send_reliable("CMD_ENCODER_READ", {"encoder_id": encoder_id})
        if callback and ok:
            # Response will come through telemetry
            pass

    # ==================== Ultrasonic Control ====================

    def ultrasonic_attach(self, sensor_id: int) -> None:
        """Attach ultrasonic sensor."""
        self._schedule(self._ultrasonic_attach_async(sensor_id))

    def ultrasonic_read(self, sensor_id: int, callback: Optional[Callable[[float], None]] = None) -> None:
        """Read ultrasonic distance."""
        self._schedule(self._ultrasonic_read_async(sensor_id, callback))

    async def _ultrasonic_attach_async(self, sensor_id: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_ULTRASONIC_ATTACH", {"sensor_id": sensor_id})

    async def _ultrasonic_read_async(self, sensor_id: int, callback: Optional[Callable[[float], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        ok, error = await client.send_reliable("CMD_ULTRASONIC_READ", {"sensor_id": sensor_id})
        # Response comes through telemetry

    # ==================== Signal Bus Control ====================

    def signal_define(self, signal_id: int, name: str, kind: str, initial: float = 0.0) -> None:
        """Define a new signal."""
        self._schedule(self._signal_define_async(signal_id, name, kind, initial))

    def signal_set(self, signal_id: int, value: float) -> None:
        """Set signal value."""
        self._schedule(self._signal_set_async(signal_id, value))

    def signal_get(self, signal_id: int, callback: Optional[Callable[[float], None]] = None) -> None:
        """Get signal value."""
        self._schedule(self._signal_get_async(signal_id, callback))

    def signals_list(self, callback: Optional[Callable[[list], None]] = None) -> None:
        """List all signals."""
        self._schedule(self._signals_list_async(callback))

    def signals_clear(self) -> None:
        """Clear all signals."""
        self._schedule(self._signals_clear_async())

    def signal_delete(self, signal_id: int) -> None:
        """Delete a signal."""
        self._schedule(self._signal_delete_async(signal_id))

    async def _signal_define_async(self, signal_id: int, name: str, kind: str, initial: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNAL_DEFINE", {
            "signal_id": signal_id, "name": name, "kind": kind, "initial": initial
        })

    async def _signal_set_async(self, signal_id: int, value: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNAL_SET", {"signal_id": signal_id, "value": value})

    async def _signal_get_async(self, signal_id: int, callback: Optional[Callable[[float], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNAL_GET", {"signal_id": signal_id})

    async def _signals_list_async(self, callback: Optional[Callable[[list], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNALS_LIST", {})

    async def _signals_clear_async(self) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNALS_CLEAR", {})

    async def _signal_delete_async(self, signal_id: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SIGNAL_DELETE", {"signal_id": signal_id})

    # ==================== Controller Slot Control ====================

    def controller_config(self, slot: int, config: dict) -> None:
        """Configure a controller slot."""
        self._schedule(self._controller_config_async(slot, config))

    def controller_enable(self, slot: int, enable: bool) -> None:
        """Enable/disable a controller slot."""
        self._schedule(self._controller_enable_async(slot, enable))

    def controller_set_param(self, slot: int, key: str, value: float) -> None:
        """Set a controller parameter."""
        self._schedule(self._controller_set_param_async(slot, key, value))

    def controller_set_param_array(self, slot: int, key: str, values: list) -> None:
        """Set a controller parameter array (for matrices)."""
        self._schedule(self._controller_set_param_array_async(slot, key, values))

    def controller_reset(self, slot: int) -> None:
        """Reset a controller slot."""
        self._schedule(self._controller_reset_async(slot))

    def controller_status(self, slot: int, callback: Optional[Callable[[dict], None]] = None) -> None:
        """Get controller status."""
        self._schedule(self._controller_status_async(slot, callback))

    async def _controller_config_async(self, slot: int, config: dict) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        payload = {"slot": slot}
        payload.update(config)
        await client.send_reliable("CMD_CTRL_SLOT_CONFIG", payload)

    async def _controller_enable_async(self, slot: int, enable: bool) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SLOT_ENABLE", {"slot": slot, "enable": enable})

    async def _controller_set_param_async(self, slot: int, key: str, value: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SLOT_SET_PARAM", {"slot": slot, "key": key, "value": value})

    async def _controller_set_param_array_async(self, slot: int, key: str, values: list) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SLOT_SET_PARAM_ARRAY", {"slot": slot, "key": key, "values": values})

    async def _controller_reset_async(self, slot: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SLOT_RESET", {"slot": slot})

    async def _controller_status_async(self, slot: int, callback: Optional[Callable[[dict], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_CTRL_SLOT_STATUS", {"slot": slot})

    # ==================== Observer Slot Control ====================

    def observer_config(self, slot: int, config: dict) -> None:
        """Configure an observer slot."""
        self._schedule(self._observer_config_async(slot, config))

    def observer_enable(self, slot: int, enable: bool) -> None:
        """Enable/disable an observer slot."""
        self._schedule(self._observer_enable_async(slot, enable))

    def observer_set_param(self, slot: int, key: str, value: float) -> None:
        """Set an observer parameter."""
        self._schedule(self._observer_set_param_async(slot, key, value))

    def observer_set_param_array(self, slot: int, key: str, values: list) -> None:
        """Set an observer parameter array (for matrices)."""
        self._schedule(self._observer_set_param_array_async(slot, key, values))

    def observer_reset(self, slot: int) -> None:
        """Reset an observer slot."""
        self._schedule(self._observer_reset_async(slot))

    def observer_status(self, slot: int, callback: Optional[Callable[[dict], None]] = None) -> None:
        """Get observer status."""
        self._schedule(self._observer_status_async(slot, callback))

    async def _observer_config_async(self, slot: int, config: dict) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        payload = {"slot": slot}
        payload.update(config)
        await client.send_reliable("CMD_OBSERVER_CONFIG", payload)

    async def _observer_enable_async(self, slot: int, enable: bool) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_OBSERVER_ENABLE", {"slot": slot, "enable": enable})

    async def _observer_set_param_async(self, slot: int, key: str, value: float) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_OBSERVER_SET_PARAM", {"slot": slot, "key": key, "value": value})

    async def _observer_set_param_array_async(self, slot: int, key: str, values: list) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_OBSERVER_SET_PARAM_ARRAY", {"slot": slot, "key": key, "values": values})

    async def _observer_reset_async(self, slot: int) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_OBSERVER_RESET", {"slot": slot})

    async def _observer_status_async(self, slot: int, callback: Optional[Callable[[dict], None]]) -> None:
        if not self._connection_service or not self._connection_service.client:
            return
        client = self._connection_service.client
        await client.send_reliable("CMD_OBSERVER_STATUS", {"slot": slot})
