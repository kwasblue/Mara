# mara_host/services/control/result.py
"""
Service result types for control operations.

Provides a consistent result pattern across all services.
"""

from dataclasses import dataclass, field
from typing import Optional, Any


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
