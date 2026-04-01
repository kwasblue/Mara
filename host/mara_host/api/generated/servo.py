# AUTO-GENERATED from ActuatorDef("servo")
# Do not edit directly - modify schema/hardware/_actuators.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class ServoState:
    """PWM servo motor (hobby servos, 50Hz) state."""
    pass  # No telemetry fields


class Servo:
    """
    PWM servo motor (hobby servos, 50Hz)

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

    async def servo_attach(self, servo_id: int, channel: int, min_us: int = 1000, max_us: int = 2000) -> None:
        """Attach a servo ID to a physical pin."""
        await self._robot.client.send_json_cmd("CMD_SERVO_ATTACH", {"servo_id": servo_id, "channel": channel, "min_us": min_us, "max_us": max_us})

    async def servo_detach(self, servo_id: int) -> None:
        """Detach a servo ID."""
        await self._robot.client.send_json_cmd("CMD_SERVO_DETACH", {"servo_id": servo_id})

    async def servo_set_angle(self, servo_id: int, angle_deg: float, duration_ms: int = 0) -> None:
        """Set servo angle in degrees."""
        await self._robot.client.send_json_cmd("CMD_SERVO_SET_ANGLE", {"servo_id": servo_id, "angle_deg": angle_deg, "duration_ms": duration_ms})

    async def servo_set_pulse(self, servo_id: int, pulse_us: int) -> None:
        """Set servo pulse width in microseconds."""
        await self._robot.client.send_json_cmd("CMD_SERVO_SET_PULSE", {"servo_id": servo_id, "pulse_us": pulse_us})

