# mara_host/api/velocity.py
"""
Velocity streaming controller for differential drive robots.

Example:
    from mara_host import Robot, VelocityController

    async with Robot("/dev/ttyUSB0") as robot:
        vel = VelocityController(robot)

        # Stream velocity commands
        await vel.set(vx=0.5, omega=0.1)
        await asyncio.sleep(1.0)
        await vel.stop()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


class VelocityController:
    """
    High-rate velocity command streaming for differential drive robots.

    Optimized for control loops running at 20-100Hz. Uses binary encoding
    when available for minimal latency and bandwidth.

    Args:
        robot: Connected Robot instance
        use_binary: Use binary encoding for efficiency (default: True)

    Example - Control loop:
        vel = VelocityController(robot)

        async def control_loop():
            while running:
                # Get desired velocity from your controller
                vx, omega = compute_velocity(target, state)

                # Send to robot (uses binary protocol)
                await vel.set(vx, omega)

                await asyncio.sleep(0.02)  # 50Hz

        await vel.stop()

    Example - Teleop:
        vel = VelocityController(robot)

        async def on_joystick(axis_x, axis_y):
            vx = axis_y * MAX_SPEED      # Forward/backward
            omega = axis_x * MAX_TURN    # Turn rate
            await vel.set(vx, omega)
    """

    def __init__(
        self,
        robot: Robot,
        use_binary: bool = True,
    ) -> None:
        self._robot = robot
        self._use_binary = use_binary
        self._last_vx = 0.0
        self._last_omega = 0.0

    @property
    def client(self):
        """Access underlying client."""
        return self._robot.client

    @property
    def current_velocity(self) -> tuple[float, float]:
        """Last commanded velocity (vx, omega)."""
        return (self._last_vx, self._last_omega)

    @property
    def is_moving(self) -> bool:
        """Whether robot is commanded to move."""
        return self._last_vx != 0.0 or self._last_omega != 0.0

    async def set(self, vx: float, omega: float) -> None:
        """
        Set robot velocity.

        Args:
            vx: Linear velocity in m/s (positive = forward)
            omega: Angular velocity in rad/s (positive = counter-clockwise)

        Uses binary encoding for minimal latency when streaming.

        Note: This is a fire-and-forget command with no ACK for maximum
        throughput. If the transport is disconnected, an exception will
        propagate and _last_vx/_last_omega will not be updated. Callers
        should handle transport errors at the control loop level.
        """
        if self._use_binary:
            # Binary protocol: 9 bytes vs ~50 bytes JSON
            await self.client.send_vel_binary(vx, omega)
        else:
            await self.client.send_auto("CMD_SET_VEL", {"vx": vx, "omega": omega})

        self._last_vx = vx
        self._last_omega = omega

    async def stop(self) -> None:
        """Stop the robot (set velocity to zero)."""
        await self.set(0.0, 0.0)

    async def set_linear(self, vx: float) -> None:
        """Set linear velocity only (keep current angular velocity)."""
        await self.set(vx, self._last_omega)

    async def set_angular(self, omega: float) -> None:
        """Set angular velocity only (keep current linear velocity)."""
        await self.set(self._last_vx, omega)

    def __repr__(self) -> str:
        if self.is_moving:
            return f"VelocityController(vx={self._last_vx:.2f}, omega={self._last_omega:.2f})"
        return "VelocityController(stopped)"
