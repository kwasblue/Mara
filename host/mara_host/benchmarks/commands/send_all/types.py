# mara_host/benchmarks/commands/send_all/types.py
"""Type definitions for send_all benchmark."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


Payload = Dict[str, Any]
PayloadSpec = Union[Payload, List[Payload]]
PayloadMap = Dict[str, PayloadSpec]


@dataclass
class CmdResult:
    """Result of sending a single command."""
    cmd: str
    ok: bool
    skipped: bool
    latency_ms: Optional[float]
    error: Optional[str]
    payload: Payload
    ack: Optional[Dict[str, Any]]


@dataclass
class RunContext:
    """Runtime context for tracking dependencies and state."""
    control_available: bool = True
    signals_defined_ok: bool = True
    slot_config_ok: bool = True
