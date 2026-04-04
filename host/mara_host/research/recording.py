# mara_host/research/recording.py
"""
Compatibility shim for research code after promotion to observability module.

The recording infrastructure has been promoted to mara_host.observability.
This module re-exports the classes with their original names for backwards
compatibility with existing research scripts.

New code should import directly from mara_host.observability:
    from mara_host.observability import ObservabilityBus, RecordingTransport
"""
from __future__ import annotations

# Re-export with original names for backwards compatibility
from mara_host.observability.recording import (
    ObservabilityBus as RecordingEventBus,
    RecordingConfig,
    RecordingTransport,
)

__all__ = [
    "RecordingEventBus",
    "RecordingConfig",
    "RecordingTransport",
]
