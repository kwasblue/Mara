# mara_host/core/shutdown.py
"""
Structured shutdown utilities for graceful component teardown.

Replaces ad-hoc contextlib.suppress(Exception) patterns with error collection
and proper logging during shutdown sequences.
"""

from dataclasses import dataclass, field
from typing import List, Callable, Awaitable, Any, Tuple
import logging

_log = logging.getLogger(__name__)


@dataclass
class ShutdownError:
    """Error encountered during shutdown of a component."""
    component: str
    error: Exception


@dataclass
class ShutdownResult:
    """Result of a shutdown sequence."""
    success: bool
    errors: List[ShutdownError] = field(default_factory=list)


async def shutdown_gracefully(
    components: List[Tuple[str, Callable[[], Awaitable[Any]]]],
    continue_on_error: bool = True,
) -> ShutdownResult:
    """
    Shutdown components in order with error collection.

    Unlike contextlib.suppress(Exception), this collects all errors and logs them
    for debugging, rather than silently swallowing exceptions.

    Args:
        components: List of (name, async_stop_func) tuples defining shutdown order
        continue_on_error: If True, continue shutting down remaining components
                          even if one fails. If False, stop on first error.

    Returns:
        ShutdownResult with success status and any collected errors

    Example:
        components = [
            ("heartbeat", self._cancel_heartbeat),
            ("connection_monitor", self.connection.stop_monitoring),
            ("transport", self._stop_transport),
        ]
        result = await shutdown_gracefully(components)
        if result.errors:
            log.warning(f"Shutdown had {len(result.errors)} errors")
    """
    errors: List[ShutdownError] = []

    for name, stop_func in components:
        try:
            await stop_func()
        except Exception as e:
            errors.append(ShutdownError(component=name, error=e))
            _log.warning(f"Error stopping {name}: {e}")
            if not continue_on_error:
                break

    return ShutdownResult(success=len(errors) == 0, errors=errors)
