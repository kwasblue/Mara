# mara_host/services/transport/robot_control.py
"""
Robot control service.

Provides high-level robot control methods that wrap the MaraClient
commands with additional conveniences.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

from mara_host.command.client import MaraClient


@dataclass
class ServoConfig:
    """Servo configuration."""
    servo_id: int
    pin: int
    min_us: int = 500
    max_us: int = 2500
    initial_angle: float = 90.0


class RobotControlService:
    """
    High-level robot control service.

    Provides convenient methods for controlling robot hardware
    with built-in safety and state tracking.

    Example:
        control = RobotControlService(client)

        # Arm and activate
        await control.arm()
        await control.activate()

        # Control servo
        await control.servo_attach(0, 13)
        await control.servo_set(0, 45)

        # Cleanup
        await control.safe_shutdown()
    """

    def __init__(self, client: MaraClient):
        """
        Initialize robot control service.

        Args:
            client: Connected MaraClient
        """
        self.client = client
        self._armed = False
        self._active = False
        self._attached_servos: set[int] = set()

    # -------------------------------------------------------------------------
    # State management
    # -------------------------------------------------------------------------

    async def arm(self) -> None:
        """Arm the robot."""
        await self.client.cmd_arm()
        self._armed = True

    async def disarm(self) -> None:
        """Disarm the robot."""
        await self.client.cmd_disarm()
        self._armed = False

    async def activate(self) -> None:
        """Set mode to ACTIVE."""
        await self.client.cmd_activate()
        self._active = True

    async def deactivate(self) -> None:
        """Set mode to IDLE."""
        await self.client.cmd_deactivate()
        self._active = False

    async def estop(self) -> None:
        """Emergency stop - immediately stops all motion."""
        await self.client.cmd_estop()
        self._armed = False
        self._active = False

    async def safe_shutdown(self) -> None:
        """Safely shut down the robot (stop motors, disarm, deactivate)."""
        try:
            await self.client.cmd_stop()
        except Exception:
            pass

        try:
            await self.deactivate()
        except Exception:
            pass

        try:
            await self.disarm()
        except Exception:
            pass

        # Detach all servos
        for servo_id in list(self._attached_servos):
            try:
                await self.servo_detach(servo_id)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # LED control
    # -------------------------------------------------------------------------

    async def led_on(self) -> None:
        """Turn LED on."""
        await self.client.cmd_led_on()

    async def led_off(self) -> None:
        """Turn LED off."""
        await self.client.cmd_led_off()

    async def led_blink(self, count: int = 3, interval_s: float = 0.2) -> None:
        """
        Blink the LED.

        Args:
            count: Number of blinks
            interval_s: Time between on/off transitions
        """
        for _ in range(count):
            await self.led_on()
            await asyncio.sleep(interval_s)
            await self.led_off()
            await asyncio.sleep(interval_s)

    # -------------------------------------------------------------------------
    # Servo control
    # -------------------------------------------------------------------------

    async def servo_attach(
        self,
        servo_id: int,
        pin: int,
        min_us: int = 500,
        max_us: int = 2500
    ) -> None:
        """
        Attach a servo to a GPIO pin.

        Args:
            servo_id: Servo ID (0-15)
            pin: GPIO pin number
            min_us: Minimum pulse width in microseconds
            max_us: Maximum pulse width in microseconds
        """
        await self.client.cmd_servo_attach(servo_id, pin, min_us, max_us)
        self._attached_servos.add(servo_id)

    async def servo_detach(self, servo_id: int) -> None:
        """Detach a servo."""
        await self.client.cmd_servo_detach(servo_id)
        self._attached_servos.discard(servo_id)

    async def servo_set(
        self,
        servo_id: int,
        angle: float,
        duration_ms: int = 0
    ) -> None:
        """
        Set servo angle.

        Args:
            servo_id: Servo ID
            angle: Target angle (0-180 degrees)
            duration_ms: Movement duration (0 = immediate)
        """
        await self.client.cmd_servo_set_angle(servo_id, angle, duration_ms)

    async def servo_sweep(
        self,
        servo_id: int,
        start_angle: float = 0,
        end_angle: float = 180,
        step: float = 10,
        delay_s: float = 0.1
    ) -> None:
        """
        Sweep a servo through a range of angles.

        Args:
            servo_id: Servo ID
            start_angle: Starting angle
            end_angle: Ending angle
            step: Angle increment per step
            delay_s: Delay between steps
        """
        angle = start_angle
        direction = 1 if end_angle > start_angle else -1
        step = abs(step) * direction

        while (direction > 0 and angle <= end_angle) or \
              (direction < 0 and angle >= end_angle):
            await self.servo_set(servo_id, angle)
            await asyncio.sleep(delay_s)
            angle += step

    # -------------------------------------------------------------------------
    # Motor control
    # -------------------------------------------------------------------------

    async def motor_set(self, motor_id: int, speed_percent: float) -> None:
        """
        Set DC motor speed.

        Args:
            motor_id: Motor ID
            speed_percent: Speed from -100 to 100 (percent)
        """
        # Clamp and convert to -1.0 to 1.0
        speed_percent = max(-100, min(100, speed_percent))
        await self.client.cmd_dc_set_speed(motor_id, speed_percent / 100.0)

    async def motor_stop(self, motor_id: int) -> None:
        """Stop a DC motor."""
        await self.client.cmd_dc_set_speed(motor_id, 0.0)

    async def motor_stop_all(self) -> None:
        """Stop all motors."""
        await self.client.cmd_stop()

    # -------------------------------------------------------------------------
    # GPIO control
    # -------------------------------------------------------------------------

    async def gpio_write(self, channel: int, high: bool) -> None:
        """
        Write to a GPIO channel.

        Args:
            channel: GPIO channel number
            high: True for HIGH, False for LOW
        """
        await self.client.cmd_gpio_write(channel, high)

    async def gpio_mode(self, channel: int, mode: str) -> None:
        """
        Set GPIO channel mode.

        Args:
            channel: GPIO channel number
            mode: "input", "output", "input_pullup", "input_pulldown"
        """
        await self.client.cmd_gpio_mode(channel, mode)

    # -------------------------------------------------------------------------
    # Velocity control
    # -------------------------------------------------------------------------

    async def set_velocity(self, vx: float, omega: float) -> None:
        """
        Set robot velocity.

        Args:
            vx: Forward velocity (m/s)
            omega: Angular velocity (rad/s)
        """
        await self.client.cmd_set_vel(vx, omega)

    async def stop_motion(self) -> None:
        """Stop all motion."""
        await self.client.cmd_stop()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def is_armed(self) -> bool:
        """Check if robot is armed."""
        return self._armed

    @property
    def is_active(self) -> bool:
        """Check if robot is in active mode."""
        return self._active

    @property
    def attached_servos(self) -> set[int]:
        """Get set of attached servo IDs."""
        return self._attached_servos.copy()
