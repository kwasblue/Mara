# mara_host/core/__init__.py
"""
Core infrastructure: protocol, events, base classes.

This is an INTERNAL module. For public API, use mara_host top-level imports.

Internal API (for mara_host submodules):
    - BaseModule: Abstract base for runtime modules
    - EventBus: Pub/sub event system
    - CommandHostModule, EventHostModule: Host module base classes
    - Protocol functions: encode, extract_frames, crc16_ccitt
    - MsgType: Message type enum
    - Settings classes: TransportSettings, HostSettings, etc.
"""

from .base_module import BaseModule
from .event_bus import EventBus
from .host_module import CommandHostModule, EventHostModule
from .messages import MsgType
from .protocol import encode, extract_frames, crc16_ccitt
from .settings import (
    TransportSettings,
    MQTTSettings,
    FeatureSettings,
    EncoderDefaults,
    HostSettings,
)
from .result import Result

__all__ = [
    # Base classes
    "BaseModule",
    "EventBus",
    "CommandHostModule",
    "EventHostModule",
    # Protocol
    "MsgType",
    "encode",
    "extract_frames",
    "crc16_ccitt",
    # Settings
    "TransportSettings",
    "MQTTSettings",
    "FeatureSettings",
    "EncoderDefaults",
    "HostSettings",
    # Result
    "Result",
]
