"""
Typed protocol message classes.

These dataclasses replace nested dicts for protocol messages, providing
type safety, IDE autocomplete, and clearer code.

Generated message types:
- IdentityMessage: Handshake identity response from firmware
- CommandMessage: Outgoing command to firmware
- CommandAck: Incoming command acknowledgment from firmware
- TelemetryMessage: Telemetry data from firmware
- RawFrame: Unhandled frame data
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class IdentityMessage:
    """Handshake identity response from firmware."""

    firmware: str = "unknown"
    protocol: int = 0
    schema_version: int = 0
    capabilities: int = 0
    features: tuple[str, ...] = ()
    board: str = "unknown"
    name: str = "unknown"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IdentityMessage:
        """Parse from JSON dict received from firmware."""
        features = data.get("features", [])
        if isinstance(features, list):
            features = tuple(features)
        return cls(
            firmware=data.get("firmware", "unknown"),
            protocol=data.get("protocol", 0),
            schema_version=data.get("schema_version", 0),
            capabilities=data.get("capabilities", 0),
            features=features,
            board=data.get("board", "unknown"),
            name=data.get("name", "unknown"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "firmware": self.firmware,
            "protocol": self.protocol,
            "schema_version": self.schema_version,
            "capabilities": self.capabilities,
            "features": list(self.features),
            "board": self.board,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class CommandMessage:
    """Outgoing command to firmware."""

    type: str
    seq: int
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for wire transmission."""
        return {
            "kind": "cmd",
            "type": self.type,
            "seq": self.seq,
            **self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandMessage:
        """Parse from dict (for testing/debugging)."""
        # Extract known fields, rest goes to payload
        cmd_type = data.get("type", "")
        seq = data.get("seq", 0)
        payload = {k: v for k, v in data.items() if k not in ("kind", "type", "seq")}
        return cls(type=cmd_type, seq=seq, payload=payload)


@dataclass(frozen=True, slots=True)
class CommandAck:
    """Incoming command acknowledgment from firmware."""

    cmd: str
    seq: int
    ok: bool
    error: Optional[str] = None
    error_code: Optional[int] = None
    state: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandAck:
        """Parse from JSON dict received from firmware."""
        # Extract known fields, rest goes to data
        known_fields = {"cmd", "seq", "ok", "error", "error_code", "state", "src"}
        extra = {k: v for k, v in data.items() if k not in known_fields}
        return cls(
            cmd=data.get("cmd", ""),
            seq=data.get("seq", -1),
            ok=data.get("ok", False),
            error=data.get("error"),
            error_code=data.get("error_code"),
            state=data.get("state"),
            data=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        result: dict[str, Any] = {
            "cmd": self.cmd,
            "seq": self.seq,
            "ok": self.ok,
            "src": "mcu",
        }
        if self.error is not None:
            result["error"] = self.error
        if self.error_code is not None:
            result["error_code"] = self.error_code
        if self.state is not None:
            result["state"] = self.state
        if self.data:
            result.update(self.data)
        return result

    @property
    def success(self) -> bool:
        """Alias for ok field."""
        return self.ok


@dataclass(frozen=True, slots=True)
class TelemetryMessage:
    """Telemetry data from firmware."""

    timestamp_ms: int = 0
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TelemetryMessage:
        """Parse from JSON dict received from firmware."""
        timestamp = data.get("timestamp_ms", data.get("t", 0))
        payload = {k: v for k, v in data.items() if k not in ("type", "timestamp_ms", "t")}
        return cls(timestamp_ms=timestamp, data=payload)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {"timestamp_ms": self.timestamp_ms, **self.data}


@dataclass(frozen=True, slots=True)
class RawFrame:
    """Unhandled frame data for unknown message types."""

    msg_type: int
    payload: bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {"msg_type": self.msg_type, "payload": self.payload}


@dataclass(frozen=True, slots=True)
class HelloMessage:
    """Hello message from firmware during connection."""

    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HelloMessage:
        """Parse from JSON dict."""
        payload = {k: v for k, v in data.items() if k != "type"}
        return cls(data=payload)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict representation."""
        return {"type": "HELLO", **self.data}


# Type aliases for common response patterns
CommandResult = tuple[bool, Optional[str]]  # (success, error_msg)
CommandResultWithData = tuple[bool, Optional[str], Optional[dict[str, Any]]]


__all__ = [
    "IdentityMessage",
    "CommandMessage",
    "CommandAck",
    "TelemetryMessage",
    "RawFrame",
    "HelloMessage",
    "CommandResult",
    "CommandResultWithData",
]
