# mara_host/mcp/errors.py
"""
Structured error handling for MCP tools.

Provides error types with recovery hints that help LLMs
understand what went wrong and what to do next.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Error codes for MCP tool failures."""
    NOT_CONNECTED = "NOT_CONNECTED"
    NOT_ARMED = "NOT_ARMED"
    NOT_ACTIVE = "NOT_ACTIVE"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    HARDWARE_ERROR = "HARDWARE_ERROR"
    TIMEOUT = "TIMEOUT"
    ALREADY_CONNECTED = "ALREADY_CONNECTED"
    ALREADY_ARMED = "ALREADY_ARMED"
    ROBOT_NOT_LOADED = "ROBOT_NOT_LOADED"
    COMMAND_FAILED = "COMMAND_FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class StructuredError:
    """
    Structured error response for LLM consumption.

    The next_action field tells the LLM exactly what to do next,
    closing the recovery loop without requiring the LLM to reason about it.
    """
    success: bool
    error: ErrorCode
    message: str
    next_action: str | None = None
    details: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Convert to JSON string for MCP response."""
        return json.dumps({
            "success": self.success,
            "error": self.error.value,
            "message": self.message,
            "next_action": self.next_action,
            "details": self.details,
        })


@dataclass
class StructuredResult:
    """
    Structured success response for LLM consumption.
    """
    success: bool
    data: dict[str, Any] | None = None
    message: str | None = None

    def to_json(self) -> str:
        """Convert to JSON string for MCP response."""
        result = {"success": self.success}
        if self.data:
            result["data"] = self.data
        if self.message:
            result["message"] = self.message
        return json.dumps(result)


# Common error responses
def not_connected_error() -> StructuredError:
    """Robot is not connected."""
    return StructuredError(
        success=False,
        error=ErrorCode.NOT_CONNECTED,
        message="Not connected to robot. Call mara_connect() first.",
        next_action="mara_connect",
    )


def not_armed_error() -> StructuredError:
    """Robot is not armed for actuator commands."""
    return StructuredError(
        success=False,
        error=ErrorCode.NOT_ARMED,
        message="Robot must be armed before actuator commands. Call mara_arm() first.",
        next_action="mara_arm",
    )


def not_active_error() -> StructuredError:
    """Robot is not in ACTIVE state."""
    return StructuredError(
        success=False,
        error=ErrorCode.NOT_ACTIVE,
        message="Robot must be activated for this command. Call mara_activate() first.",
        next_action="mara_activate",
    )


def robot_not_loaded_error() -> StructuredError:
    """Robot configuration not loaded."""
    return StructuredError(
        success=False,
        error=ErrorCode.ROBOT_NOT_LOADED,
        message="Robot configuration not loaded. Call mara_robot_describe(config_path=...) first.",
        next_action="mara_robot_describe",
    )


def invalid_parameter_error(param: str, reason: str) -> StructuredError:
    """Invalid parameter value."""
    return StructuredError(
        success=False,
        error=ErrorCode.INVALID_PARAMETER,
        message=f"Invalid parameter '{param}': {reason}",
        next_action=None,
        details={"parameter": param, "reason": reason},
    )


def hardware_error(component: str, reason: str) -> StructuredError:
    """Hardware-level error."""
    return StructuredError(
        success=False,
        error=ErrorCode.HARDWARE_ERROR,
        message=f"Hardware error on {component}: {reason}",
        next_action="mara_get_health",
        details={"component": component, "reason": reason},
    )


def timeout_error(operation: str, timeout_ms: int) -> StructuredError:
    """Operation timed out."""
    return StructuredError(
        success=False,
        error=ErrorCode.TIMEOUT,
        message=f"Operation '{operation}' timed out after {timeout_ms}ms. Check connection and retry.",
        next_action="mara_get_health",
        details={"operation": operation, "timeout_ms": timeout_ms},
    )


def command_failed_error(command: str, reason: str) -> StructuredError:
    """Command execution failed."""
    return StructuredError(
        success=False,
        error=ErrorCode.COMMAND_FAILED,
        message=f"Command '{command}' failed: {reason}",
        next_action="mara_get_state",
        details={"command": command, "reason": reason},
    )


def wrap_exception(e: Exception, context: str = "") -> StructuredError:
    """Wrap a generic exception into a structured error."""
    error_str = str(e)

    # Detect common error patterns and provide specific guidance
    if "not connected" in error_str.lower():
        return not_connected_error()
    if "not armed" in error_str.lower():
        return not_armed_error()
    if "timeout" in error_str.lower():
        return timeout_error(context or "unknown", 0)

    return StructuredError(
        success=False,
        error=ErrorCode.UNKNOWN,
        message=f"{context}: {error_str}" if context else error_str,
        next_action="mara_get_health",
    )
