"""Discoverable control-graph transform definitions."""

from ..discovery import discover_defs

TRANSFORM_DEFS = discover_defs(__file__, __name__, "TRANSFORM")

__all__ = ["TRANSFORM_DEFS"]
