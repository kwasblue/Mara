# mara_host/core/result.py
"""
Standard result types for MARA operations.

Provides a consistent result pattern across all layers:
services, workflows, and public API.
"""

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class Result:
    """
    Standard result type for all operations.

    Provides a consistent way to return success/failure with optional
    data across all MARA APIs.

    Attributes:
        ok: Whether the operation succeeded
        error: Error message if operation failed
        data: Operation-specific result data
        state: Optional state after operation (for state-changing commands)

    Example:
        # Service returning result
        def arm() -> Result:
            if can_arm:
                return Result.success({"state": "ARMED"}, state="ARMED")
            else:
                return Result.failure("Cannot arm: safety check failed")

        # Consumer using result
        result = service.arm()
        if result.ok:
            print(f"Armed: {result.data}")
        else:
            print(f"Failed: {result.error}")

        # Boolean context
        if result:
            print("Success!")
    """

    ok: bool
    error: Optional[str] = None
    data: Optional[Any] = None
    state: Optional[str] = None

    @classmethod
    def success(cls, data: Any = None, state: Optional[str] = None) -> "Result":
        """
        Create a successful result.

        Args:
            data: Optional result data
            state: Optional state after operation

        Returns:
            Result with ok=True
        """
        return cls(ok=True, data=data, state=state)

    @classmethod
    def failure(cls, error: str, data: Any = None, state: Optional[str] = None) -> "Result":
        """
        Create a failure result.

        Args:
            error: Error message
            data: Optional context data
            state: Optional state after operation

        Returns:
            Result with ok=False
        """
        return cls(ok=False, error=error, data=data, state=state)

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.ok

    def __repr__(self) -> str:
        if self.ok:
            return f"Result.success({self.data!r})"
        else:
            return f"Result.failure({self.error!r})"

    def unwrap(self) -> Any:
        """
        Get data or raise error.

        Returns:
            Result data if successful

        Raises:
            RuntimeError: If result is a failure
        """
        if not self.ok:
            raise RuntimeError(self.error or "Operation failed")
        return self.data

    def unwrap_or(self, default: Any) -> Any:
        """
        Get data or return default.

        Args:
            default: Value to return if failed

        Returns:
            Result data if successful, otherwise default
        """
        return self.data if self.ok else default

    def map(self, fn) -> "Result":
        """
        Transform data if successful.

        Args:
            fn: Function to apply to data

        Returns:
            New Result with transformed data, or same failure
        """
        if self.ok:
            return Result.success(fn(self.data))
        return self

    def and_then(self, fn) -> "Result":
        """
        Chain operations.

        Args:
            fn: Function that returns a Result

        Returns:
            Result from fn if successful, or same failure
        """
        if self.ok:
            return fn(self.data)
        return self


# Backwards compatibility alias
ServiceResult = Result


async def send_command(
    client: "MaraClient",
    command: str,
    payload: dict,
    default_error: str,
    *,
    success_data: dict[str, Any] | None = None,
) -> Result:
    """
    Send a command and return a Result.

    Simplifies the common pattern:
        ok, error = await client.send_reliable(...)
        if ok:
            return Result.success(data=...)
        else:
            return Result.failure(error=error or "default")

    Args:
        client: MaraClient instance
        command: Command name
        payload: Command payload
        default_error: Default error message if no error returned
        success_data: Data dict for successful result

    Returns:
        Result

    Example:
        return await send_command(
            self.client,
            "CMD_GPIO_WRITE",
            {"channel": channel, "value": value},
            f"Failed to write GPIO channel {channel}",
            success_data={"channel": channel, "value": value},
        )
    """
    ok, error = await client.send_reliable(command, payload)
    if ok:
        return Result.success(data=success_data)
    return Result.failure(error=error or default_error)
