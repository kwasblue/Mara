"""Control-graph schema registry.

This registry is the single source of truth for runtime-configurable control-graph
node kinds. Add one file under sources/, transforms/, or sinks/ and regenerate.
"""

from .core import GraphTypeDef, ParamDef, SinkDef, SourceDef, TransformDef
from .sources import SOURCE_DEFS
from .transforms import TRANSFORM_DEFS
from .sinks import SINK_DEFS

CONTROL_GRAPH_TYPES: dict[str, GraphTypeDef] = {
    **SOURCE_DEFS,
    **TRANSFORM_DEFS,
    **SINK_DEFS,
}

__all__ = [
    "GraphTypeDef",
    "ParamDef",
    "SourceDef",
    "TransformDef",
    "SinkDef",
    "SOURCE_DEFS",
    "TRANSFORM_DEFS",
    "SINK_DEFS",
    "CONTROL_GRAPH_TYPES",
]
