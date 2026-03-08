# mara_host/services/control/state_service.py
"""
State management service for robot lifecycle control.

Provides arm/disarm/activate/estop operations with state tracking
and consistent result handling.
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from mara_host.services.control.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class RobotState(str, Enum):
    """Robot state machine states."""

    UNKNOWN = "UNKNOWN"
    IDLE = "IDLE"
    ARMED = "ARMED"
    ACTIVE = "ACTIVE"
    ESTOP = "ESTOP"
    ERROR = "ERROR"


class StateService:
    """
    Stateful service for robot state management.

    Handles state machine transitions (arm, disarm, activate, estop)
    and tracks current state.

    Example:
        state_svc = StateService(client)

        result = await state_svc.arm()
        if result.ok:
            print(f"State: {state_svc.current_state}")

        result = await state_svc.activate()
        if not result.ok:
            print(f"Failed to activate: {result.error}")

        # Emergency stop
        await state_svc.estop()
    """

    def __init__(self, client: "MaraClient"):
        """
        Initialize state service.

        Args:
            client: Connected MaraClient instance
        """
        self.client = client
        self._state = RobotState.UNKNOWN

    @property
    def current_state(self) -> RobotState:
        """Get current robot state."""
        return self._state

    @property
    def is_armed(self) -> bool:
        """Check if robot is armed (ARMED or ACTIVE)."""
        return self._state in (RobotState.ARMED, RobotState.ACTIVE)

    @property
    def is_active(self) -> bool:
        """Check if robot is in active mode."""
        return self._state == RobotState.ACTIVE

    @property
    def is_estopped(self) -> bool:
        """Check if robot is in emergency stop state."""
        return self._state == RobotState.ESTOP

    async def arm(self) -> ServiceResult:
        """
        Arm the robot (IDLE -> ARMED).

        Returns:
            ServiceResult with success/failure and current state
        """
        ok, error = await self.client.arm()
        if ok:
            self._state = RobotState.ARMED
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to arm",
                state=self._state.value,
            )

    async def disarm(self) -> ServiceResult:
        """
        Disarm the robot (ARMED -> IDLE).

        Returns:
            ServiceResult with success/failure and current state
        """
        ok, error = await self.client.disarm()
        if ok:
            self._state = RobotState.IDLE
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to disarm",
                state=self._state.value,
            )

    async def activate(self) -> ServiceResult:
        """
        Activate the robot (ARMED -> ACTIVE).

        Motion commands are accepted in ACTIVE state.

        Returns:
            ServiceResult with success/failure and current state
        """
        ok, error = await self.client.activate()
        if ok:
            self._state = RobotState.ACTIVE
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to activate",
                state=self._state.value,
            )

    async def deactivate(self) -> ServiceResult:
        """
        Deactivate the robot (ACTIVE -> ARMED).

        Returns:
            ServiceResult with success/failure and current state
        """
        ok, error = await self.client.deactivate()
        if ok:
            self._state = RobotState.ARMED
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to deactivate",
                state=self._state.value,
            )

    async def estop(self) -> ServiceResult:
        """
        Emergency stop the robot.

        Immediately stops all motion and enters ESTOP state.
        Requires clear_estop() before normal operation can resume.

        Returns:
            ServiceResult (always succeeds locally)
        """
        ok, error = await self.client.estop()
        # E-STOP should always succeed locally even if comms fail
        self._state = RobotState.ESTOP
        if ok:
            return ServiceResult.success(state=self._state.value)
        else:
            # Still mark as estopped but note the communication error
            return ServiceResult(
                ok=True,
                state=self._state.value,
                error=f"E-STOP applied locally; MCU comms: {error}",
            )

    async def clear_estop(self) -> ServiceResult:
        """
        Clear emergency stop (ESTOP -> IDLE).

        Returns:
            ServiceResult with success/failure and current state
        """
        ok, error = await self.client.clear_estop()
        if ok:
            self._state = RobotState.IDLE
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to clear E-STOP",
                state=self._state.value,
            )

    async def stop(self) -> ServiceResult:
        """
        Stop all motion (soft stop).

        Unlike E-STOP, this just zeroes velocities without
        changing robot state.

        Returns:
            ServiceResult with success/failure
        """
        ok, error = await self.client.cmd_stop()
        if ok:
            return ServiceResult.success(state=self._state.value)
        else:
            return ServiceResult.failure(
                error=error or "Failed to stop",
                state=self._state.value,
            )

    async def safe_shutdown(self) -> ServiceResult:
        """
        Safely shut down the robot.

        Attempts to: stop motion, deactivate, disarm.
        Ignores errors to ensure cleanup completes.

        Returns:
            ServiceResult (always succeeds)
        """
        # Best-effort cleanup
        try:
            await self.client.cmd_stop()
        except Exception:
            pass

        try:
            await self.client.deactivate()
        except Exception:
            pass

        try:
            await self.client.disarm()
        except Exception:
            pass

        self._state = RobotState.IDLE
        return ServiceResult.success(state=self._state.value)

    def set_state(self, state: RobotState) -> None:
        """
        Manually set the state (for sync with external updates).

        Args:
            state: New robot state
        """
        self._state = state

    def sync_from_telemetry(self, state_str: str) -> None:
        """
        Sync state from telemetry data.

        Args:
            state_str: State string from telemetry (e.g., "ARMED")
        """
        try:
            self._state = RobotState(state_str.upper())
        except ValueError:
            self._state = RobotState.UNKNOWN
