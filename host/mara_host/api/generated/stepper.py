# AUTO-GENERATED from ActuatorDef("stepper")
# Do not edit directly - modify schema/hardware/_actuators.py instead.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..robot import Robot


@dataclass
class StepperState:
    """Stepper motor with step/dir driver (A4988, DRV8825, TMC2209) state."""
    motor_id: int = 0
    attached: int = 0
    enabled: int = 0
    moving: int = 0
    dir_forward: int = 0
    last_cmd_steps: int = 0
    speed_centi: int = 0
    ts_ms: int = 0


class Stepper:
    """
    Stepper motor with step/dir driver (A4988, DRV8825, TMC2209)

    Interface: gpio
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

    async def stepper_enable(self, stepper_id: int, enable: bool = True) -> None:
        """Enable or disable a stepper driver (via enable pin)."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_ENABLE", {"stepper_id": stepper_id, "enable": enable})

    async def stepper_move_rel(self, stepper_id: int, steps: int, speed_rps: float = 1.0) -> None:
        """Move a stepper a relative number of steps."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_MOVE_REL", {"stepper_id": stepper_id, "steps": steps, "speed_rps": speed_rps})

    async def stepper_move_deg(self, stepper_id: int, degrees: float, speed_rps: float = 1.0) -> None:
        """Move a stepper a relative number of degrees."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_MOVE_DEG", {"stepper_id": stepper_id, "degrees": degrees, "speed_rps": speed_rps})

    async def stepper_move_rev(self, stepper_id: int, revolutions: float, speed_rps: float = 1.0) -> None:
        """Move a stepper a relative number of revolutions."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_MOVE_REV", {"stepper_id": stepper_id, "revolutions": revolutions, "speed_rps": speed_rps})

    async def stepper_stop(self, stepper_id: int) -> None:
        """Immediately stop a stepper motor."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_STOP", {"stepper_id": stepper_id})

    async def stepper_get_position(self, stepper_id: int) -> None:
        """Get the current position of a stepper motor in steps."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_GET_POSITION", {"stepper_id": stepper_id})

    async def stepper_reset_position(self, stepper_id: int) -> None:
        """Reset the stepper position counter to zero."""
        await self._robot.client.send_json_cmd("CMD_STEPPER_RESET_POSITION", {"stepper_id": stepper_id})

