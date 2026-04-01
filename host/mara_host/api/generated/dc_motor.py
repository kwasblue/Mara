# AUTO-GENERATED from ActuatorDef("dc_motor")
# Do not edit directly - modify schema/hardware/_actuators.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class DcMotorState:
    """Brushed DC motor with H-bridge driver state."""
    attached: int = 0
    speed_centi: int = 0
    ts_ms: int = 0


class DcMotor:
    """
    Brushed DC motor with H-bridge driver

    Interface: pwm
    """

    def __init__(self, robot: "Robot", actuator_id: int = 0) -> None:
        self._robot = robot
        self._actuator_id = actuator_id

    @property
    def robot(self) -> "Robot":
        return self._robot

    @property
    def actuator_id(self) -> int:
        return self._actuator_id

    async def dc_set_speed(self, motor_id: int, speed: float) -> None:
        """Set DC motor speed and direction for a given motor ID."""
        await self._robot.client.send_json_cmd("CMD_DC_SET_SPEED", {"motor_id": motor_id, "speed": speed})

    async def dc_stop(self, motor_id: int) -> None:
        """Stop a DC motor (set speed to zero)."""
        await self._robot.client.send_json_cmd("CMD_DC_STOP", {"motor_id": motor_id})

    async def dc_vel_pid_enable(self, motor_id: int, enable: bool) -> None:
        """Enable or disable closed-loop velocity PID control for a DC motor."""
        await self._robot.client.send_json_cmd("CMD_DC_VEL_PID_ENABLE", {"motor_id": motor_id, "enable": enable})

    async def dc_set_vel_target(self, motor_id: int, omega: float) -> None:
        """Set desired angular velocity target for a DC motor's PID controller."""
        await self._robot.client.send_json_cmd("CMD_DC_SET_VEL_TARGET", {"motor_id": motor_id, "omega": omega})

    async def dc_set_vel_gains(self, motor_id: int, kp: float, ki: float, kd: float) -> None:
        """Configure PID gains for DC motor velocity control."""
        await self._robot.client.send_json_cmd("CMD_DC_SET_VEL_GAINS", {"motor_id": motor_id, "kp": kp, "ki": ki, "kd": kd})

