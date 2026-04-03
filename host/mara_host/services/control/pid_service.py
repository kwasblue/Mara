# mara_host/services/control/pid_service.py
"""
PID controller service.

Provides high-level control for velocity PID controllers on DC motors.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class PidGains:
    """PID controller gains."""

    kp: float = 1.0  # Proportional gain
    ki: float = 0.0  # Integral gain
    kd: float = 0.0  # Derivative gain
    output_min: float = -1.0  # Output minimum
    output_max: float = 1.0  # Output maximum
    integral_max: float = 1.0  # Integral windup limit


@dataclass
class PidState:
    """PID controller state."""

    motor_id: int
    enabled: bool = False
    target: float = 0.0  # Target velocity
    gains: Optional[PidGains] = None


class PidService:
    """
    Service for velocity PID control.

    Manages PID velocity controllers on DC motors.
    This is a plain class (not ConfigurableService) as it manages
    per-motor PID state.

    Example:
        pid_svc = PidService(client)

        # Enable velocity PID on motor 0
        await pid_svc.enable(0)

        # Set PID gains
        await pid_svc.set_gains(0, kp=1.0, ki=0.1, kd=0.01)

        # Set velocity target
        await pid_svc.set_target(0, 5.0)  # 5 rad/s

        # Disable PID
        await pid_svc.disable(0)
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize PID service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._states: dict[int, PidState] = {}

    def get_state(self, motor_id: int) -> PidState:
        """
        Get or create PID state for a motor.

        Args:
            motor_id: Motor ID

        Returns:
            PidState
        """
        if motor_id not in self._states:
            self._states[motor_id] = PidState(motor_id=motor_id)
        return self._states[motor_id]

    async def enable(self, motor_id: int) -> ServiceResult:
        """
        Enable velocity PID on a motor.

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_DC_VEL_PID_ENABLE",
            {
                "motor_id": motor_id,
                "enable": True,
            },
        )

        if ok:
            state = self.get_state(motor_id)
            state.enabled = True
            return ServiceResult.success(
                data={"motor_id": motor_id, "enabled": True}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to enable PID on motor {motor_id}"
            )

    async def disable(self, motor_id: int) -> ServiceResult:
        """
        Disable velocity PID on a motor.

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_DC_VEL_PID_ENABLE",
            {
                "motor_id": motor_id,
                "enable": False,
            },
        )

        if ok:
            state = self.get_state(motor_id)
            state.enabled = False
            return ServiceResult.success(
                data={"motor_id": motor_id, "enabled": False}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to disable PID on motor {motor_id}"
            )

    async def set_gains(
        self,
        motor_id: int,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_min: Optional[float] = None,
        output_max: Optional[float] = None,
        integral_max: Optional[float] = None,
    ) -> ServiceResult:
        """
        Set PID gains for a motor.

        Args:
            motor_id: Motor ID
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_min: Output minimum (optional)
            output_max: Output maximum (optional)
            integral_max: Integral windup limit (optional)

        Returns:
            ServiceResult
        """
        payload = {
            "motor_id": motor_id,
            "kp": kp,
            "ki": ki,
            "kd": kd,
        }
        if output_min is not None:
            payload["output_min"] = output_min
        if output_max is not None:
            payload["output_max"] = output_max
        if integral_max is not None:
            payload["integral_max"] = integral_max

        ok, error = await self.client.send_reliable(
            "CMD_DC_SET_VEL_GAINS",
            payload,
        )

        if ok:
            state = self.get_state(motor_id)
            state.gains = PidGains(
                kp=kp,
                ki=ki,
                kd=kd,
                output_min=output_min if output_min is not None else -1.0,
                output_max=output_max if output_max is not None else 1.0,
                integral_max=integral_max if integral_max is not None else 1.0,
            )
            return ServiceResult.success(data=payload)
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set PID gains on motor {motor_id}"
            )

    async def set_target(self, motor_id: int, omega: float) -> ServiceResult:
        """
        Set velocity target for PID control.

        Args:
            motor_id: Motor ID
            omega: Target angular velocity in rad/s

        Returns:
            ServiceResult
        """
        ok, error = await self.client.send_reliable(
            "CMD_DC_SET_VEL_TARGET",
            {
                "motor_id": motor_id,
                "omega": omega,
            },
        )

        if ok:
            state = self.get_state(motor_id)
            state.target = omega
            return ServiceResult.success(
                data={"motor_id": motor_id, "omega": omega}
            )
        else:
            return ServiceResult.failure(
                error=error or f"Failed to set velocity target on motor {motor_id}"
            )

    async def stop(self, motor_id: int) -> ServiceResult:
        """
        Stop PID control and motor.

        Disables PID and sends stop command.

        Args:
            motor_id: Motor ID

        Returns:
            ServiceResult
        """
        # Disable PID first
        pid_result = await self.disable(motor_id)

        # Then stop motor
        ok, error = await self.client.send_reliable(
            "CMD_DC_STOP",
            {"motor_id": motor_id},
        )

        if ok:
            state = self.get_state(motor_id)
            state.target = 0.0
            return ServiceResult.success(data={"motor_id": motor_id})
        else:
            # Chain PID disable error if both operations failed
            stop_error = error or f"Failed to stop motor {motor_id}"
            if not pid_result.ok:
                stop_error = f"{stop_error}; PID disable also failed: {pid_result.error}"
            return ServiceResult.failure(error=stop_error)

    def is_enabled(self, motor_id: int) -> bool:
        """
        Check if PID is enabled on a motor.

        Args:
            motor_id: Motor ID

        Returns:
            True if PID is enabled
        """
        if motor_id in self._states:
            return self._states[motor_id].enabled
        return False

    def get_gains(self, motor_id: int) -> Optional[PidGains]:
        """
        Get current PID gains for a motor.

        Args:
            motor_id: Motor ID

        Returns:
            PidGains or None if not set
        """
        if motor_id in self._states:
            return self._states[motor_id].gains
        return None
