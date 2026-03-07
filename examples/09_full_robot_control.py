#!/usr/bin/env python3
"""
Example 09: Full Robot Control

Demonstrates a complete robot control application:
- Connection management
- State machine control
- Real-time telemetry processing
- Closed-loop velocity control
- Safety monitoring
- Session recording

This example shows how to combine all mara_host components
into a cohesive control application.

Prerequisites:
- ESP32 with motors and sensors connected
- Safe testing environment (robot will move!)

Usage:
    python 09_full_robot_control.py /dev/ttyUSB0
    python 09_full_robot_control.py tcp:192.168.1.100

WARNING: Robot will move! Ensure safe testing environment.
"""
import asyncio
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport
from mara_host.command.client import AsyncRobotClient
from mara_host.motor.motion import MotionHostModule
from mara_host.sensor.encoder import EncoderHostModule, EncoderDefaults
from mara_host.telemetry.host_module import TelemetryHostModule
from mara_host.core.event_bus import EventBus
from mara_host.logger.logger import MaraLogBundle
from mara_host.research.recording import RecordingEventBus, RecordingTransport


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class RobotControlConfig:
    """Configuration for robot control."""
    # Encoder settings
    encoder_counts_per_rev: int = 1000
    wheel_radius_m: float = 0.05
    wheel_base_m: float = 0.2

    # Control settings
    control_rate_hz: float = 50.0
    velocity_timeout_s: float = 0.5  # Stop if no command for this long

    # Safety limits
    max_linear_vel_mps: float = 0.5
    max_angular_vel_rps: float = 1.0

    # Telemetry
    telemetry_enabled: bool = True
    recording_enabled: bool = True


# =============================================================================
# Robot State
# =============================================================================

@dataclass
class RobotState:
    """Current robot state."""
    # Pose (estimated from encoders)
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    # Velocities
    vx: float = 0.0
    omega: float = 0.0

    # Encoder data
    left_ticks: int = 0
    right_ticks: int = 0

    # IMU data
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0
    gx: float = 0.0
    gy: float = 0.0
    gz: float = 0.0

    # Status
    connected: bool = False
    armed: bool = False
    activated: bool = False
    estopped: bool = False

    # Timestamps
    last_telemetry_time: float = 0.0
    last_command_time: float = 0.0


# =============================================================================
# Robot Controller
# =============================================================================

class RobotController:
    """
    High-level robot controller combining all modules.
    """

    def __init__(
        self,
        transport_arg: str,
        config: Optional[RobotControlConfig] = None,
    ):
        self.config = config or RobotControlConfig()
        self.state = RobotState()
        self._running = False
        self._control_task: Optional[asyncio.Task] = None

        # Setup recording if enabled
        if self.config.recording_enabled:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("control_logs")
            output_dir.mkdir(exist_ok=True)

            self._bundle = MaraLogBundle(
                name=f"control_{timestamp}",
                log_dir=str(output_dir),
                console=False,
            )

            base_transport = self._create_transport(transport_arg)
            base_bus = EventBus()

            self._transport = RecordingTransport(base_transport, self._bundle)
            self._bus = RecordingEventBus(base_bus, self._bundle)
        else:
            self._bundle = None
            self._transport = self._create_transport(transport_arg)
            self._bus = EventBus()

        # Create client
        self._client = AsyncRobotClient(
            transport=self._transport,
            bus=self._bus,
        )

        # Create modules
        self._motion = MotionHostModule(self._bus, self._client)
        self._telemetry = TelemetryHostModule(self._bus)
        self._encoder = EncoderHostModule(self._bus, self._client)

        # Subscribe to events
        self._setup_subscriptions()

    def _create_transport(self, arg: str):
        if arg.startswith("tcp:"):
            host = arg[4:]
            port = 8080
            if ":" in host:
                host, port_str = host.rsplit(":", 1)
                port = int(port_str)
            return AsyncTcpTransport(host=host, port=port)
        else:
            return SerialTransport(port=arg, baudrate=115200)

    def _setup_subscriptions(self):
        """Setup event subscriptions."""

        def on_imu(data):
            self.state.ax = data.get("ax", 0)
            self.state.ay = data.get("ay", 0)
            self.state.az = data.get("az", 0)
            self.state.gx = data.get("gx", 0)
            self.state.gy = data.get("gy", 0)
            self.state.gz = data.get("gz", 0)
            self.state.last_telemetry_time = time.monotonic()

        def on_encoder(data):
            self.state.left_ticks = data.get("ticks", 0)
            # Note: In a real system, you'd have separate left/right encoders

        def on_motor(data):
            # Could track motor current, PWM, etc.
            pass

        def on_connection_lost(_):
            self.state.connected = False
            print("[Controller] Connection lost!")

        def on_connection_restored(_):
            self.state.connected = True
            print("[Controller] Connection restored!")

        self._bus.subscribe("telemetry.imu", on_imu)
        self._bus.subscribe("telemetry.encoder0", on_encoder)
        self._bus.subscribe("telemetry.dc_motor0", on_motor)
        self._bus.subscribe("connection.lost", on_connection_lost)
        self._bus.subscribe("connection.restored", on_connection_restored)

    async def start(self):
        """Start the controller."""
        print("Starting robot controller...")

        if self._bundle:
            self._bundle.events.write("controller.start")

        await self._client.start()
        self.state.connected = True

        print(f"Connected to {self._client.robot_name}")
        print(f"Firmware: {self._client.firmware_version}")

        # Enable telemetry
        if self.config.telemetry_enabled:
            await self._client.send_reliable("CMD_TELEMETRY_ON", {})

        # Start control loop
        self._running = True
        self._control_task = asyncio.create_task(self._control_loop())

    async def stop(self):
        """Stop the controller."""
        print("Stopping robot controller...")

        self._running = False

        # Stop control loop
        if self._control_task:
            self._control_task.cancel()
            try:
                await self._control_task
            except asyncio.CancelledError:
                pass

        # Safe shutdown
        try:
            await self._motion.stop()
            await self._client.deactivate()
            await self._client.disarm()
        except:
            pass

        # Disable telemetry
        try:
            await self._client.send_reliable("CMD_TELEMETRY_OFF", {})
        except:
            pass

        if self._bundle:
            self._bundle.events.write("controller.stop")

        await self._client.stop()
        print("Controller stopped.")

    async def arm_and_activate(self) -> bool:
        """Arm and activate the robot."""
        success, error = await self._client.arm()
        if not success:
            print(f"ARM failed: {error}")
            return False
        self.state.armed = True

        success, error = await self._client.activate()
        if not success:
            print(f"ACTIVATE failed: {error}")
            return False
        self.state.activated = True

        return True

    async def set_velocity(self, vx: float, omega: float):
        """Set velocity command (with limits)."""
        # Apply limits
        vx = max(-self.config.max_linear_vel_mps,
                min(self.config.max_linear_vel_mps, vx))
        omega = max(-self.config.max_angular_vel_rps,
                   min(self.config.max_angular_vel_rps, omega))

        self.state.vx = vx
        self.state.omega = omega
        self.state.last_command_time = time.monotonic()

        await self._motion.set_velocity(vx, omega)

    async def estop(self):
        """Emergency stop."""
        await self._motion.estop()
        self.state.estopped = True
        self.state.activated = False

    async def _control_loop(self):
        """Background control loop."""
        dt = 1.0 / self.config.control_rate_hz

        while self._running:
            try:
                await asyncio.sleep(dt)

                # Safety: timeout if no commands
                if self.state.activated:
                    time_since_cmd = time.monotonic() - self.state.last_command_time
                    if time_since_cmd > self.config.velocity_timeout_s:
                        # Auto-stop if no recent commands
                        if abs(self.state.vx) > 0.01 or abs(self.state.omega) > 0.01:
                            print("[Controller] Command timeout - stopping")
                            await self._motion.stop()
                            self.state.vx = 0
                            self.state.omega = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Controller] Control loop error: {e}")


# =============================================================================
# Demo Trajectories
# =============================================================================

async def run_square_trajectory(controller: RobotController, side_length: float = 0.5):
    """Run a square trajectory."""
    print("\nRunning square trajectory...")

    for i in range(4):
        # Forward
        print(f"  Side {i+1}/4: Forward")
        await controller.set_velocity(0.2, 0.0)
        await asyncio.sleep(side_length / 0.2)

        # Stop
        await controller.set_velocity(0.0, 0.0)
        await asyncio.sleep(0.3)

        # Turn 90 degrees (pi/2 radians)
        print(f"  Side {i+1}/4: Turn")
        await controller.set_velocity(0.0, 0.5)
        await asyncio.sleep(1.57 / 0.5)  # pi/2 radians at 0.5 rad/s

        # Stop
        await controller.set_velocity(0.0, 0.0)
        await asyncio.sleep(0.3)

    print("  Square complete!")


async def run_figure_eight(controller: RobotController):
    """Run a figure-8 trajectory."""
    print("\nRunning figure-8 trajectory...")

    # First loop (left)
    print("  First loop (left)")
    await controller.set_velocity(0.2, 0.4)
    await asyncio.sleep(3.14 / 0.4)  # 180 degrees

    # Second loop (right)
    print("  Second loop (right)")
    await controller.set_velocity(0.2, -0.4)
    await asyncio.sleep(6.28 / 0.4)  # 360 degrees

    # Complete first loop
    print("  Completing first loop")
    await controller.set_velocity(0.2, 0.4)
    await asyncio.sleep(3.14 / 0.4)  # 180 degrees

    await controller.set_velocity(0.0, 0.0)
    print("  Figure-8 complete!")


# =============================================================================
# Main
# =============================================================================

async def main():
    if len(sys.argv) < 2:
        print("Usage: python 09_full_robot_control.py <port_or_tcp>")
        return

    print("="*60)
    print("Full Robot Control Example")
    print("="*60)
    print()
    print("WARNING: Robot will move! Ensure safe testing environment.")
    print("Press Enter to continue or Ctrl+C to abort...")

    try:
        input()
    except KeyboardInterrupt:
        print("Aborted.")
        return

    config = RobotControlConfig(
        max_linear_vel_mps=0.3,
        max_angular_vel_rps=0.8,
        recording_enabled=True,
    )

    controller = RobotController(sys.argv[1], config)

    try:
        # Start controller
        await controller.start()

        # Show initial state
        print(f"\nInitial state:")
        print(f"  Connected: {controller.state.connected}")
        print(f"  Armed: {controller.state.armed}")
        print(f"  Activated: {controller.state.activated}")

        # Arm and activate
        print("\nArming and activating...")
        if not await controller.arm_and_activate():
            print("Failed to arm/activate. Aborting.")
            return

        print(f"\nRobot ready!")
        print(f"  Armed: {controller.state.armed}")
        print(f"  Activated: {controller.state.activated}")

        # Run demo trajectories
        print("\n" + "="*40)
        print("Running demo trajectories")
        print("="*40)

        # Simple motion test
        print("\n1. Simple forward/backward test")
        await controller.set_velocity(0.2, 0.0)
        await asyncio.sleep(1.0)
        await controller.set_velocity(-0.2, 0.0)
        await asyncio.sleep(1.0)
        await controller.set_velocity(0.0, 0.0)
        await asyncio.sleep(0.5)

        # Rotation test
        print("\n2. Rotation test")
        await controller.set_velocity(0.0, 0.5)
        await asyncio.sleep(2.0)
        await controller.set_velocity(0.0, -0.5)
        await asyncio.sleep(2.0)
        await controller.set_velocity(0.0, 0.0)
        await asyncio.sleep(0.5)

        # Square trajectory
        await run_square_trajectory(controller, side_length=0.3)
        await asyncio.sleep(0.5)

        # Figure-8
        await run_figure_eight(controller)

        # Show final state
        print("\n" + "="*40)
        print("Final State")
        print("="*40)
        print(f"  IMU: ax={controller.state.ax:.2f}, ay={controller.state.ay:.2f}, "
              f"az={controller.state.az:.2f}")
        print(f"  Gyro: gx={controller.state.gx:.3f}, gy={controller.state.gy:.3f}, "
              f"gz={controller.state.gz:.3f}")
        print(f"  Encoder ticks: {controller.state.left_ticks}")

        print("\nDemo complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        print("Emergency stopping...")
        await controller.estop()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

        print("Emergency stopping...")
        try:
            await controller.estop()
        except:
            pass

    finally:
        await controller.stop()


if __name__ == "__main__":
    asyncio.run(main())
