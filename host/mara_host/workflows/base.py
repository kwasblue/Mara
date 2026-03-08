# mara_host/workflows/base.py
"""
Base workflow class for multi-step operations.

Provides a consistent pattern for calibration, testing, and other
workflows that need progress reporting, cancellation, and result handling.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol


class WorkflowState(Enum):
    """Workflow execution state."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class WorkflowResult:
    """
    Standard result type for workflow operations.

    Attributes:
        ok: Whether the workflow completed successfully
        error: Error message if workflow failed
        data: Workflow-specific result data
        state: Final workflow state
    """
    ok: bool
    error: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    state: WorkflowState = WorkflowState.COMPLETED

    @classmethod
    def success(cls, data: Optional[dict[str, Any]] = None) -> "WorkflowResult":
        """Create a successful result."""
        return cls(ok=True, data=data or {}, state=WorkflowState.COMPLETED)

    @classmethod
    def failure(cls, error: str) -> "WorkflowResult":
        """Create a failure result."""
        return cls(ok=False, error=error, state=WorkflowState.ERROR)

    @classmethod
    def cancelled(cls) -> "WorkflowResult":
        """Create a cancelled result."""
        return cls(ok=False, error="Cancelled", state=WorkflowState.CANCELLED)

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.ok


class MaraClientProtocol(Protocol):
    """Protocol for MaraClient compatibility."""

    async def send_reliable(self, command: str, payload: dict) -> tuple[bool, Optional[str]]:
        """Send a command with reliable delivery."""
        ...


class BaseWorkflow:
    """
    Base class for all workflows.

    Workflows encapsulate multi-step operations that may require
    user interaction, progress reporting, and cancellation support.

    Subclasses must implement:
        - run(**params) -> WorkflowResult

    Subclasses may override:
        - name: Human-readable workflow name

    Example:
        class MotorCalibrationWorkflow(BaseWorkflow):
            @property
            def name(self) -> str:
                return "Motor Calibration"

            async def run(self, motor_id: int = 0) -> WorkflowResult:
                self._emit_progress(0, "Starting calibration")
                # ... calibration logic ...
                return WorkflowResult.success({"dead_zone": 0.1})
    """

    def __init__(self, client: MaraClientProtocol):
        """
        Initialize workflow.

        Args:
            client: MaraClient instance for robot communication
        """
        self._client = client
        self._state = WorkflowState.IDLE
        self._cancelled = False

        # Callbacks - set by consumer
        self.on_progress: Callable[[int, str], None] = lambda p, s: None
        self.on_result: Callable[[WorkflowResult], None] = lambda r: None
        self.on_user_prompt: Callable[[str, list[str]], None] = lambda q, o: None

    @property
    def client(self) -> MaraClientProtocol:
        """Get the MaraClient instance."""
        return self._client

    @property
    def name(self) -> str:
        """Human-readable workflow name."""
        return self.__class__.__name__.replace("Workflow", "")

    @property
    def state(self) -> WorkflowState:
        """Get current workflow state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self._state in (WorkflowState.RUNNING, WorkflowState.WAITING_USER)

    @property
    def is_cancelled(self) -> bool:
        """Check if workflow has been cancelled."""
        return self._cancelled

    async def run(self, **params) -> WorkflowResult:
        """
        Execute the workflow.

        Args:
            **params: Workflow-specific parameters

        Returns:
            WorkflowResult with success/failure and data

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement run()")

    def cancel(self) -> None:
        """
        Request workflow cancellation.

        The workflow will stop at the next safe point.
        """
        self._cancelled = True
        self._state = WorkflowState.CANCELLED

    def reset(self) -> None:
        """Reset workflow state for reuse."""
        self._state = WorkflowState.IDLE
        self._cancelled = False

    def _emit_progress(self, percent: int, status: str) -> None:
        """
        Emit progress update.

        Args:
            percent: Progress percentage (0-100)
            status: Human-readable status message
        """
        self.on_progress(percent, status)

    def _set_state(self, state: WorkflowState) -> None:
        """Update workflow state."""
        self._state = state

    def _check_cancelled(self) -> bool:
        """
        Check if workflow has been cancelled.

        Use this in workflow loops to allow early termination.

        Returns:
            True if cancelled, False otherwise
        """
        return self._cancelled

    async def _send_command(
        self,
        command: str,
        payload: dict,
    ) -> tuple[bool, Optional[str]]:
        """
        Send a command to the robot.

        Args:
            command: Command name
            payload: Command payload

        Returns:
            Tuple of (success, error_message)
        """
        return await self._client.send_reliable(command, payload)
