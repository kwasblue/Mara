# mara_host/services/control/state_service.py
"""
State management service for robot lifecycle control.

Provides arm/disarm/activate/estop operations with state tracking
and consistent result handling.

Features:
- State machine transitions (arm, disarm, activate, estop)
- State history buffer for debugging and auditing
- wait_for_state() for polling-based state synchronization
- ensure_state() for automatic transition sequencing
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional, Union, Set, List

from mara_host.core.result import ServiceResult

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


@dataclass
class StateTransition:
    """Record of a state transition for history tracking."""

    timestamp: float  # time.time()
    from_state: RobotState
    to_state: RobotState
    trigger: str  # Command or event that caused the transition
    success: bool = True  # Whether the transition succeeded
    error: Optional[str] = None  # Error message if failed


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

    def __init__(self, client: "MaraClient", history_size: int = 100):
        """
        Initialize state service.

        Args:
            client: Connected MaraClient instance
            history_size: Number of state transitions to keep in history
        """
        self.client = client
        self._state = RobotState.UNKNOWN

        # State history buffer
        self._history: deque[StateTransition] = deque(maxlen=history_size)

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

    def _record_transition(
        self,
        from_state: RobotState,
        to_state: RobotState,
        trigger: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a state transition in history.

        Args:
            from_state: State before transition
            to_state: State after transition (or attempted state)
            trigger: Command or event that caused the transition
            success: Whether the transition succeeded
            error: Error message if failed
        """
        transition = StateTransition(
            timestamp=time.time(),
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            success=success,
            error=error,
        )
        self._history.append(transition)

    def get_history(self, count: Optional[int] = None) -> List[StateTransition]:
        """
        Get state transition history.

        Args:
            count: Number of transitions to return (None = all)

        Returns:
            List of StateTransition (oldest first)
        """
        if count is None:
            return list(self._history)
        return list(self._history)[-count:]

    def get_last_transition(self) -> Optional[StateTransition]:
        """Get the most recent state transition."""
        if self._history:
            return self._history[-1]
        return None

    async def arm(self) -> ServiceResult:
        """
        Arm the robot (IDLE -> ARMED).

        Returns:
            ServiceResult with success/failure and current state
        """
        from_state = self._state
        ok, error = await self.client.arm()
        if ok:
            self._state = RobotState.ARMED
            self._record_transition(from_state, RobotState.ARMED, "CMD_ARM")
            return ServiceResult.success(state=self._state.value)
        else:
            self._record_transition(
                from_state, RobotState.ARMED, "CMD_ARM", success=False, error=error
            )
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
        from_state = self._state
        ok, error = await self.client.disarm()
        if ok:
            self._state = RobotState.IDLE
            self._record_transition(from_state, RobotState.IDLE, "CMD_DISARM")
            return ServiceResult.success(state=self._state.value)
        else:
            self._record_transition(
                from_state, RobotState.IDLE, "CMD_DISARM", success=False, error=error
            )
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
        from_state = self._state
        ok, error = await self.client.activate()
        if ok:
            self._state = RobotState.ACTIVE
            self._record_transition(from_state, RobotState.ACTIVE, "CMD_ACTIVATE")
            return ServiceResult.success(state=self._state.value)
        else:
            self._record_transition(
                from_state, RobotState.ACTIVE, "CMD_ACTIVATE", success=False, error=error
            )
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
        from_state = self._state
        ok, error = await self.client.deactivate()
        if ok:
            self._state = RobotState.ARMED
            self._record_transition(from_state, RobotState.ARMED, "CMD_DEACTIVATE")
            return ServiceResult.success(state=self._state.value)
        else:
            self._record_transition(
                from_state, RobotState.ARMED, "CMD_DEACTIVATE", success=False, error=error
            )
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
        from_state = self._state
        ok, error = await self.client.estop()
        # E-STOP should always succeed locally even if comms fail
        self._state = RobotState.ESTOP
        self._record_transition(
            from_state, RobotState.ESTOP, "CMD_ESTOP",
            success=True,  # Always mark local estop as success
            error=error if not ok else None
        )
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
        from_state = self._state
        ok, error = await self.client.clear_estop()
        if ok:
            self._state = RobotState.IDLE
            self._record_transition(from_state, RobotState.IDLE, "CMD_CLEAR_ESTOP")
            return ServiceResult.success(state=self._state.value)
        else:
            self._record_transition(
                from_state, RobotState.IDLE, "CMD_CLEAR_ESTOP", success=False, error=error
            )
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

        Records transition if state changed from external source (MCU).

        Args:
            state_str: State string from telemetry (e.g., "ARMED")
        """
        from_state = self._state
        try:
            new_state = RobotState(state_str.upper())
        except ValueError:
            new_state = RobotState.UNKNOWN

        if new_state != from_state:
            self._state = new_state
            self._record_transition(from_state, new_state, "telemetry_sync")

    async def get_state(self) -> ServiceResult:
        """
        Query current state from MCU.

        Updates local state to match MCU and returns current values.

        Returns:
            ServiceResult with state data:
                - mode: Current mode string (IDLE, ARMED, ACTIVE, ESTOP)
                - armed: True if motors enabled
                - active: True if motion commands accepted
                - estop: True if emergency stop active
        """
        ok, error, data = await self.client.send_with_data("CMD_GET_STATE", {})
        if ok and data:
            mode_str = data.get("mode", "UNKNOWN")
            try:
                self._state = RobotState(mode_str.upper())
            except ValueError:
                self._state = RobotState.UNKNOWN
            return ServiceResult.success(
                data={
                    "mode": mode_str,
                    "armed": data.get("armed", False),
                    "active": data.get("active", False),
                    "estop": data.get("estop", False),
                },
                state=self._state.value,
            )
        else:
            return ServiceResult.failure(
                error=error or "Failed to get state",
                state=self._state.value,
            )

    async def wait_for_state(
        self,
        target: Union[RobotState, Set[RobotState]],
        timeout_s: float = 5.0,
        poll_interval_s: float = 0.1,
    ) -> ServiceResult:
        """
        Wait for the robot to reach a specific state.

        Polls MCU state until the target state is reached or timeout expires.
        Use this instead of arbitrary sleep() delays after state-changing commands.

        Args:
            target: Target state(s) to wait for. Can be a single RobotState
                    or a set of acceptable states.
            timeout_s: Maximum time to wait (default: 5.0s)
            poll_interval_s: Time between state polls (default: 0.1s)

        Returns:
            ServiceResult with:
                - ok=True if target state was reached
                - ok=False if timeout or error occurred
                - state: Current state at time of return

        Example:
            # Wait for ARMED state after arm command
            await state_svc.arm()
            result = await state_svc.wait_for_state(RobotState.ARMED, timeout_s=2.0)
            if not result.ok:
                print(f"Failed to reach ARMED: {result.error}")

            # Wait for any of several acceptable states
            result = await state_svc.wait_for_state(
                {RobotState.ARMED, RobotState.ACTIVE},
                timeout_s=3.0
            )
        """
        # Normalize target to a set
        if isinstance(target, RobotState):
            target_states: Set[RobotState] = {target}
        else:
            target_states = target

        elapsed = 0.0
        while elapsed < timeout_s:
            result = await self.get_state()
            if not result.ok:
                return result  # Propagate communication error

            if self._state in target_states:
                return ServiceResult.success(
                    state=self._state.value,
                    data={"waited_s": elapsed},
                )

            await asyncio.sleep(poll_interval_s)
            elapsed += poll_interval_s

        # Timeout reached
        target_names = ", ".join(s.value for s in target_states)
        return ServiceResult.failure(
            error=f"Timeout waiting for state(s) [{target_names}]; current: {self._state.value}",
            state=self._state.value,
        )

    async def ensure_state(
        self,
        target: RobotState,
        timeout_s: float = 5.0,
    ) -> ServiceResult:
        """
        Ensure the robot is in the target state, transitioning if needed.

        Automatically executes the appropriate state transition commands
        and waits for the target state.

        Args:
            target: Desired robot state
            timeout_s: Maximum time to wait for state transition

        Returns:
            ServiceResult with success/failure

        Example:
            # Ensure robot is ACTIVE (will arm + activate if needed)
            result = await state_svc.ensure_state(RobotState.ACTIVE)
        """
        # First check current state
        result = await self.get_state()
        if not result.ok:
            return result

        if self._state == target:
            return ServiceResult.success(state=self._state.value)

        # Handle ESTOP first - must clear before any other transitions
        if self._state == RobotState.ESTOP:
            result = await self.clear_estop()
            if not result.ok:
                return result

        # Execute transitions to reach target
        if target == RobotState.IDLE:
            if self._state == RobotState.ACTIVE:
                await self.deactivate()
            if self._state in (RobotState.ARMED, RobotState.ACTIVE):
                await self.disarm()

        elif target == RobotState.ARMED:
            if self._state == RobotState.ACTIVE:
                await self.deactivate()
            elif self._state == RobotState.IDLE:
                await self.arm()

        elif target == RobotState.ACTIVE:
            if self._state == RobotState.IDLE:
                result = await self.arm()
                if not result.ok:
                    return result
            if self._state in (RobotState.IDLE, RobotState.ARMED):
                await self.activate()

        # Wait for the target state
        return await self.wait_for_state(target, timeout_s=timeout_s)
