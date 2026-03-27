"""Discoverable control-graph source definitions."""

from ..discovery import discover_defs

SOURCE_DEFS = discover_defs(__file__, __name__, "SOURCE")

__all__ = ["SOURCE_DEFS"]
