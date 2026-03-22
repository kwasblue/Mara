# mara_host/services/control/stepper_service.py
"""
Stepper motor control service.

Provides high-level control for stepper motors with position tracking.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class StepperConfig:
    """Configuration for a stepper motor."""

    stepper_id: int
    steps_per_rev: int = 200  # Full steps per revolution
    microsteps: int = 1  # Microstepping factor
    max_speed_rps: float = 10.0  # Max speed in revolutions per second
    acceleration: float = 100.0  # Steps/s^2
    inverted: bool = False


@dataclass
class StepperState:
    """Current state of a stepper motor."""

    stepper_id: int
    position: int = 0  # Current position in steps
    target_position: int = 0  # Target position
    enabled: bool = False
    moving: bool = False


class StepperService(ConfigurableService[StepperConfig, StepperState]):
    """
    Service for stepper motor control.

    Manages stepper motors with position tracking, relative/absolute
    movement, and speed control.

    Example:
        stepper_svc = StepperService(client)

        # Enable stepper
        await stepper_svc.enable(0)

        # Move relative steps
        await stepper_svc.move_relative(0, 200, speed_rps=1.0)

        # Move to absolute position
        await stepper_svc.move_to(0, 1000)

        # Stop
        await stepper_svc.stop(0)

        # Disable when done
        await stepper_svc.disable(0)
    """

    config_class = StepperConfig
    state_class = StepperState
    id_field = "stepper_id"

    def configure(
        self,
        stepper_id: int,
        steps_per_rev: int = 200,
        microsteps: int = 1,
        max_speed_rps: float = 10.0,
        acceleration: float = 100.0,
        inverted: bool = False,
    ) -> StepperConfig:
        """
        Configure a stepper motor.

        Args:
            stepper_id: Stepper ID (0-3)
            steps_per_rev: Full steps per revolution
            microsteps: Microstepping factor (1, 2, 4, 8, 16, 32)
            max_speed_rps: Maximum speed in revolutions per second
            acceleration: Acceleration in steps/s^2
            inverted: If True, invert direction

        Returns:
            StepperConfig
        """
        config = StepperConfig(
            stepper_id=stepper_id,
            steps_per_rev=steps_per_rev,
            microsteps=microsteps,
            max_speed_rps=max_speed_rps,
            acceleration=acceleration,
            inverted=inverted,
        )
        self._configs[stepper_id] = config
        return config

    @property
    def effective_steps_per_rev(self) -> int:
        """Get effective steps per revolution including microstepping."""
        return 200  # Default, should be calculated per motor

    def get_effective_steps_per_rev(self, stepper_id: int) -> int:
        """Get effective steps per revolution for a specific motor."""
        config = self.get_config(stepper_id)
        return config.steps_per_rev * config.microsteps

    async def enable(self, stepper_id: int) -> ServiceResult:
        """
        Enable a stepper motor (energize coils).

        Args:
            stepper_id: Stepper ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_ENABLE",
            {"stepper_id": stepper_id, "enable": True},
        )

        if ok:
            state = self.get_state(stepper_id)
            state.enabled = True
            return ServiceResult.success(data={"stepper_id": stepper_id, "enabled": True})
        else:
            return ServiceResult.failure(error=error or f"Failed to enable stepper {stepper_id}")

    async def disable(self, stepper_id: int) -> ServiceResult:
        """
        Disable a stepper motor (release coils).

        Args:
            stepper_id: Stepper ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_ENABLE",
            {"stepper_id": stepper_id, "enable": False},
        )

        if ok:
            state = self.get_state(stepper_id)
            state.enabled = False
            return ServiceResult.success(data={"stepper_id": stepper_id, "enabled": False})
        else:
            return ServiceResult.failure(error=error or f"Failed to disable stepper {stepper_id}")

    async def move_relative(
        self,
        stepper_id: int,
        steps: int,
        speed_rps: float = 1.0,
    ) -> ServiceResult:
        """
        Move stepper by a relative number of steps.

        Args:
            stepper_id: Stepper ID
            steps: Number of steps (negative for reverse)
            speed_rps: Speed in revolutions per second

        Returns:
            ServiceResult
        """
        config = self.get_config(stepper_id)

        # Apply inversion
        if config.inverted:
            steps = -steps

        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_MOVE_REL",
            {
                "stepper_id": stepper_id,
                "steps": steps,
                "speed_rps": speed_rps,
            },
        )

        if ok:
            state = self.get_state(stepper_id)
            state.target_position = state.position + steps
            state.moving = True
            return ServiceResult.success(
                data={"stepper_id": stepper_id, "steps": steps, "speed_rps": speed_rps}
            )
        else:
            return ServiceResult.failure(error=error or f"Failed to move stepper {stepper_id}")

    async def move_degrees(
        self,
        stepper_id: int,
        degrees: float,
        speed_rps: float = 1.0,
    ) -> ServiceResult:
        """
        Rotate stepper by angle in degrees.

        Args:
            stepper_id: Stepper ID
            degrees: Angle in degrees
            speed_rps: Speed in revolutions per second

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_MOVE_DEG",
            {
                "stepper_id": stepper_id,
                "degrees": degrees,
                "speed_rps": speed_rps,
            },
        )

        if ok:
            state = self.get_state(stepper_id)
            state.moving = True
            return ServiceResult.success(
                data={"stepper_id": stepper_id, "degrees": degrees}
            )
        else:
            return ServiceResult.failure(error=error or f"Failed to rotate stepper {stepper_id}")

    async def move_revolutions(
        self,
        stepper_id: int,
        revolutions: float,
        speed_rps: float = 1.0,
    ) -> ServiceResult:
        """
        Rotate stepper by number of revolutions.

        Args:
            stepper_id: Stepper ID
            revolutions: Number of revolutions
            speed_rps: Speed in revolutions per second

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_MOVE_REV",
            {
                "stepper_id": stepper_id,
                "revolutions": revolutions,
                "speed_rps": speed_rps,
            },
        )

        if ok:
            state = self.get_state(stepper_id)
            state.moving = True
            return ServiceResult.success(
                data={"stepper_id": stepper_id, "revolutions": revolutions}
            )
        else:
            return ServiceResult.failure(error=error or f"Failed to rotate stepper {stepper_id}")

    async def stop(self, stepper_id: int) -> ServiceResult:
        """
        Stop a stepper motor immediately.

        Args:
            stepper_id: Stepper ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_STOP",
            {"stepper_id": stepper_id},
        )

        if ok:
            state = self.get_state(stepper_id)
            state.moving = False
            return ServiceResult.success(data={"stepper_id": stepper_id})
        else:
            return ServiceResult.failure(error=error or f"Failed to stop stepper {stepper_id}")

    async def get_position(self, stepper_id: int) -> ServiceResult:
        """
        Request current position from MCU.

        Note: The actual position value comes via telemetry.

        Args:
            stepper_id: Stepper ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_GET_POS",
            {"stepper_id": stepper_id},
        )

        if ok:
            return ServiceResult.success(data={"stepper_id": stepper_id})
        else:
            return ServiceResult.failure(error=error or f"Failed to get stepper {stepper_id} position")

    async def reset_position(self, stepper_id: int) -> ServiceResult:
        """
        Reset position counter to zero.

        Args:
            stepper_id: Stepper ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_STEPPER_RESET_POS",
            {"stepper_id": stepper_id},
        )

        if ok:
            state = self.get_state(stepper_id)
            state.position = 0
            state.target_position = 0
            return ServiceResult.success(data={"stepper_id": stepper_id, "position": 0})
        else:
            return ServiceResult.failure(error=error or f"Failed to reset stepper {stepper_id} position")

    async def stop_all(self) -> ServiceResult:
        """
        Stop all stepper motors.

        Returns:
            ServiceResult
        """
        errors = []
        for stepper_id in list(self._states.keys()):
            result = await self.stop(stepper_id)
            if not result.ok:
                errors.append(f"Stepper {stepper_id}: {result.error}")

        if errors:
            return ServiceResult.failure(error="; ".join(errors))
        return ServiceResult.success()
