# mara_host/services/control/result.py
"""
Service result types for control operations.

Provides a consistent result pattern across all services.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class ServiceResult:
    """
    Standard result type for service operations.

    Attributes:
        ok: Whether the operation succeeded
        error: Error message if operation failed
        state: Current robot state after operation (if applicable)
        data: Additional result data (command-specific)

    Example:
        result = await state_service.arm()
        if result.ok:
            print(f"Armed! State: {result.state}")
        else:
            print(f"Failed: {result.error}")
    """

    ok: bool
    error: Optional[str] = None
    state: Optional[str] = None
    data: Optional[dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        state: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> "ServiceResult":
        """Create a successful result."""
        return cls(ok=True, state=state, data=data or {})

    @classmethod
    def failure(
        cls,
        error: str,
        state: Optional[str] = None,
    ) -> "ServiceResult":
        """Create a failure result."""
        return cls(ok=False, error=error, state=state)

    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.ok


async def send_command(
    client: "MaraClient",
    command: str,
    payload: dict,
    default_error: str,
    *,
    success_data: dict[str, Any] | None = None,
) -> ServiceResult:
    """
    Send a command and return a ServiceResult.

    Simplifies the common pattern:
        ok, error = await client.send_reliable(...)
        if ok:
            return ServiceResult.success(data=...)
        else:
            return ServiceResult.failure(error=error or "default")

    Args:
        client: MaraClient instance
        command: Command name
        payload: Command payload
        default_error: Default error message if no error returned
        success_data: Data dict for successful result

    Returns:
        ServiceResult

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
        return ServiceResult.success(data=success_data)
    return ServiceResult.failure(error=error or default_error)
