# mara_host/gui/core/controller.py
"""
Robot controller for GUI operations.

Bridges the async services layer with the Qt GUI thread.
Runs on a dedicated asyncio thread and emits Qt signals
for thread-safe UI updates.

This is a thin delegation layer - actual functionality is in services.
"""

import asyncio
import threading
from typing import Optional, Callable

from mara_host.gui.core.signals import GuiSignals
from mara_host.gui.core.state import AppState, ConnectionState, TransportConfig, DeviceCapabilities


class RobotController:
    """
    Async robot controller for GUI operations.

    Manages robot connection and provides high-level operations
    that emit Qt signals for UI updates. Delegates actual work
    to underlying services.

    Example:
        signals = GuiSignals()
        controller = RobotController(signals)

        # Start the async event loop
        controller.start()

        # Connect to robot (schedules async operation)
        controller.connect_serial("/dev/cu.usbserial-0001")

        # Perform operations (delegated to services)
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

        # Services (created on connect)
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
        self._disconnecting = False

    @property
    def state(self) -> AppState:
        """Get current application state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self._state.is_connected

    @property
    def client(self):
        """Get the MaraClient instance (for workflows)."""
        if self._connection_service:
            return self._connection_service.client
        return None

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

        # Schedule disconnect and wait
        if self._connection_service:
            try:
                future = self._schedule(self._disconnect_async())
                future.result(timeout=3.0)
            except Exception:
                pass

        # Cancel pending tasks
        if self._loop:
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
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _schedule(self, coro) -> asyncio.Future:
        """Schedule a coroutine on the async thread."""
        if not self._loop or not self._running:
            raise RuntimeError("Controller not started")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ==================== Connection ====================

    def connect_serial(self, port: str, baudrate: int = 115200) -> None:
        """Connect via serial transport."""
        config = TransportConfig(
            transport_type="serial",
            port=port,
            baudrate=baudrate,
        )
        self._schedule(self._connect_async(config))

    def connect_tcp(self, host: str, port: int = 3333) -> None:
        """Connect via TCP transport."""
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

        # Wait for pending disconnect
        for _ in range(30):
            if not self._disconnecting:
                break
            await asyncio.sleep(0.1)

        if self._disconnecting:
            self.signals.log_warning("Previous disconnect still in progress")
            self._disconnecting = False

        self._state.connection_state = ConnectionState.CONNECTING
        self._state.transport_config = config
        self.signals.status_message.emit("Connecting...")

        try:
            transport_type = TransportType.SERIAL if config.transport_type == "serial" else TransportType.TCP

            conn_config = ConnectionConfig(
                transport_type=transport_type,
                port=config.port,
                baudrate=config.baudrate,
                host=config.host,
                tcp_port=config.tcp_port,
            )

            self._dev_log(f"Connecting: {transport_type.value} {config.port or config.host}")
            self._connection_service = ConnectionService(conn_config)
            info = await self._connection_service.connect()
            self._dev_log(f"Connected: protocol={info.protocol_version}")

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

            # Auto-attach servos
            for servo_id in range(2):
                try:
                    await self._servo_service.attach(
                        servo_id=servo_id,
                        channel=servo_id,
                        min_us=500,
                        max_us=2500,
                        initial_angle=90,
                    )
                except Exception:
                    pass

            # Update state
            self._state.connection_state = ConnectionState.CONNECTED
            self._state.firmware_version = info.firmware_version or ""
            self._state.protocol_version = info.protocol_version or 0
            self._state.robot_state = "IDLE"
            self._state.capabilities = DeviceCapabilities(
                features=info.features or [],
                capabilities_mask=info.capabilities or 0,
            )

            # Emit signals
            self.signals.connection_changed.emit(True, f"Connected - FW: {info.firmware_version}")
            self.signals.capabilities_changed.emit(self._state.capabilities)
            self.signals.log_info(f"Connected to robot (FW: {info.firmware_version})")

        except Exception as e:
            self._state.connection_state = ConnectionState.ERROR
            self._state.last_error = str(e)
            self.signals.connection_changed.emit(False, "")
            self.signals.connection_error.emit(str(e))
            self.signals.log_error(f"Connection failed: {e}")

    async def _disconnect_async(self) -> None:
        """Internal async disconnect."""
        self._disconnecting = True
        try:
            if self._telemetry_service:
                try:
                    self._telemetry_service.stop()
                except Exception as e:
                    self.signals.log_error(f"Telemetry stop error: {e}")

            if self._connection_service:
                try:
                    await self._connection_service.disconnect()
                except Exception as e:
                    self.signals.log_error(f"Connection disconnect error: {e}")

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

    # ==================== State Control (Delegate to StateService) ====================

    def arm(self) -> None:
        self._schedule(self._state_op("arm"))

    def disarm(self) -> None:
        self._schedule(self._state_op("disarm"))

    def activate(self) -> None:
        self._schedule(self._state_op("activate"))

    def deactivate(self) -> None:
        self._schedule(self._state_op("deactivate"))

    def estop(self) -> None:
        self._schedule(self._state_op("estop"))

    def clear_estop(self) -> None:
        self._schedule(self._state_op("clear_estop"))

    async def _state_op(self, op: str) -> None:
        """Execute state operation and emit signals."""
        if not self._state_service:
            return

        self._dev_log(f"CMD: {op}()")
        method = getattr(self._state_service, op)
        result = await method()
        self._dev_log(f"RSP: {op} -> ok={result.ok}, error={result.error}")

        if result.ok:
            state_map = {
                "arm": "ARMED",
                "disarm": "IDLE",
                "activate": "ACTIVE",
                "deactivate": "ARMED",
                "estop": "ESTOP",
                "clear_estop": "IDLE",
            }
            new_state = state_map.get(op, "UNKNOWN")
            self.signals.state_changed.emit(new_state)
            self.signals.log_info(f"Robot {op}ed" if op != "estop" else "E-STOP ACTIVATED")

            if op == "estop":
                self._state.estop_active = True
            elif op == "clear_estop":
                self._state.estop_active = False
        else:
            self.signals.status_error.emit(result.error or f"{op} failed")

    # ==================== Motion Control (Delegate to MotionService) ====================

    def set_velocity(self, vx: float, omega: float) -> None:
        self._schedule(self._motion_op("set_velocity", vx, omega))

    def stop_motion(self) -> None:
        self._schedule(self._motion_op("stop"))

    async def _motion_op(self, op: str, *args) -> None:
        if not self._motion_service:
            return
        method = getattr(self._motion_service, op)
        await method(*args)

    # ==================== Motor Control (Delegate to MotorService) ====================

    def set_motor_speed(self, motor_id: int, speed: float) -> None:
        self._schedule(self._motor_op("set_speed_fast", motor_id, speed))

    def stop_motor(self, motor_id: int) -> None:
        self._schedule(self._motor_op("stop", motor_id))

    async def _motor_op(self, op: str, *args) -> None:
        if not self._motor_service:
            return
        method = getattr(self._motor_service, op)
        await method(*args)

    # ==================== Servo Control (Delegate to ServoService) ====================

    def set_servo_angle(self, servo_id: int, angle: float) -> None:
        self._schedule(self._servo_op("set_angle_fast", servo_id, angle))

    def set_servo_angle_reliable(self, servo_id: int, angle: float) -> None:
        self._schedule(self._servo_op("set_angle", servo_id, angle))

    async def _servo_op(self, op: str, *args) -> None:
        if not self._servo_service:
            return
        method = getattr(self._servo_service, op)
        await method(*args)

    # ==================== GPIO Control (Delegate to GpioService) ====================

    def gpio_write(self, channel: int, value: int) -> None:
        self._schedule(self._gpio_op("write", channel, value))

    def gpio_toggle(self, channel: int) -> None:
        self._schedule(self._gpio_op("toggle", channel))

    async def _gpio_op(self, op: str, *args) -> None:
        if not self._gpio_service:
            return
        method = getattr(self._gpio_service, op)
        await method(*args)

    # ==================== Telemetry Callbacks ====================

    def _on_state_changed(self, state: str) -> None:
        self._state.robot_state = state
        self.signals.state_changed.emit(state)

    def _on_imu_data(self, imu) -> None:
        self.signals.imu_data.emit(imu)

    # ==================== Signal Bus Control ====================

    def signal_define(self, signal_id: int, name: str, kind: str, initial: float) -> None:
        """Define a signal in the signal bus."""
        self.send_command("CMD_CTRL_SIGNAL_DEFINE", {
            "signal_id": signal_id,
            "name": name,
            "signal_kind": kind,
            "initial_value": initial,
        })

    def signal_delete(self, signal_id: int) -> None:
        """Delete a signal from the signal bus."""
        self.send_command("CMD_CTRL_SIGNAL_DELETE", {"signal_id": signal_id})

    def signal_set(self, signal_id: int, value: float) -> None:
        """Set a signal value."""
        self.send_command("CMD_CTRL_SIGNAL_SET", {"signal_id": signal_id, "value": value})

    def signals_clear(self) -> None:
        """Clear all signals from the signal bus."""
        self.send_command("CMD_CTRL_SIGNALS_CLEAR", {})

    def signals_list(self) -> None:
        """Request list of all signals."""
        self.send_command("CMD_CTRL_SIGNALS_LIST", {})

    # ==================== Controller Slot Control ====================

    def controller_config(self, slot: int, config: dict) -> None:
        """Configure a controller slot."""
        self.send_command("CMD_CTRL_SLOT_CONFIG", {"slot": slot, **config})

    def controller_enable(self, slot: int, enable: bool) -> None:
        """Enable or disable a controller slot."""
        self.send_command("CMD_CTRL_SLOT_ENABLE", {"slot": slot, "enable": enable})

    def controller_reset(self, slot: int) -> None:
        """Reset a controller slot."""
        self.send_command("CMD_CTRL_SLOT_RESET", {"slot": slot})

    def controller_set_param(self, slot: int, key: str, value: float) -> None:
        """
        Set a single controller parameter (hot-swap capable).

        This is more efficient than full reconfiguration for live tuning.
        Supports: kp, ki, kd, out_min, out_max, i_min, i_max
        """
        self.send_command("CMD_CTRL_SLOT_SET_PARAM", {
            "slot": slot,
            "key": key,
            "value": value,
        })

    def controller_set_param_array(self, slot: int, key: str, values: list) -> None:
        """Set controller matrix parameters (for state-space)."""
        self.send_command("CMD_CTRL_SLOT_SET_PARAM_ARRAY", {
            "slot": slot,
            "key": key,
            "values": values,
        })

    # ==================== Observer Slot Control ====================

    def observer_config(self, slot: int, config: dict) -> None:
        """Configure an observer slot."""
        self.send_command("CMD_OBSERVER_CONFIG", {"slot": slot, **config})

    def observer_enable(self, slot: int, enable: bool) -> None:
        """Enable or disable an observer slot."""
        self.send_command("CMD_OBSERVER_ENABLE", {"slot": slot, "enable": enable})

    def observer_reset(self, slot: int) -> None:
        """Reset an observer slot."""
        self.send_command("CMD_OBSERVER_RESET", {"slot": slot})

    def observer_set_param(self, slot: int, key: str, value: float) -> None:
        """
        Set a single observer parameter (hot-swap capable).

        Supports observer gain tuning at runtime.
        """
        self.send_command("CMD_OBSERVER_SET_PARAM", {
            "slot": slot,
            "key": key,
            "value": value,
        })

    def observer_set_param_array(self, slot: int, key: str, values: list) -> None:
        """Set observer matrix parameters (A, B, C, L matrices)."""
        self.send_command("CMD_OBSERVER_SET_PARAM_ARRAY", {
            "slot": slot,
            "key": key,
            "values": values,
        })

    # ==================== Generic Command Interface ====================

    def send_command(
        self,
        command: str,
        payload: dict,
        callback: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        """Send an arbitrary command."""
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
