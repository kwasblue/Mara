"""Discoverable control-graph sink definitions."""

from ..discovery import discover_defs

SINK_DEFS = discover_defs(__file__, __name__, "SINK")

__all__ = ["SINK_DEFS"]
