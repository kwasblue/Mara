#!/usr/bin/env python3
"""Generate control-graph registry artifacts from the schema registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
HOST_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(HOST_DIR.parent))

from mara_host.tools.schema.control_graph import CONTROL_GRAPH_TYPES, SINK_DEFS, SOURCE_DEFS, TRANSFORM_DEFS
from mara_host.tools.schema.control_graph.schema import GRAPH_SCHEMA_VERSION, graph_json_schema
from mara_host.tools.schema.paths import PY_CONFIG_DIR

JSON_OUT = PY_CONFIG_DIR / "control_graph_registry.json"
PY_OUT = PY_CONFIG_DIR / "control_graph_defs.py"
GRAPH_JSON_SCHEMA_OUT = PY_CONFIG_DIR / "control_graph_schema.json"
SCHEMA_VERSION = GRAPH_SCHEMA_VERSION


def _sorted_dict(defs: dict[str, object]) -> dict[str, object]:
    return {name: defs[name] for name in sorted(defs)}


def generate_json() -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        "sources": {name: spec.to_dict() for name, spec in _sorted_dict(SOURCE_DEFS).items()},
        "transforms": {name: spec.to_dict() for name, spec in _sorted_dict(TRANSFORM_DEFS).items()},
        "sinks": {name: spec.to_dict() for name, spec in _sorted_dict(SINK_DEFS).items()},
    }
    return json.dumps(data, indent=2)


def _param_expr(spec) -> str:
    kwargs: list[str] = [f"name={spec.name!r}", f"type={spec.type!r}"]
    if spec.description:
        kwargs.append(f"description={spec.description!r}")
    if spec.required:
        kwargs.append("required=True")
    if spec.default is not None:
        kwargs.append(f"default={spec.default!r}")
    if spec.minimum is not None:
        kwargs.append(f"minimum={spec.minimum!r}")
    if spec.maximum is not None:
        kwargs.append(f"maximum={spec.maximum!r}")
    if spec.enum is not None:
        kwargs.append(f"enum={list(spec.enum)!r}")
    if spec.unit is not None:
        kwargs.append(f"unit={spec.unit!r}")
    return f"ParamDef({', '.join(kwargs)})"


def _graph_type_expr(spec) -> str:
    cls_name = {
        "source": "SourceDef",
        "transform": "TransformDef",
        "sink": "SinkDef",
    }[spec.category]
    kwargs: list[str] = [f"kind={spec.kind!r}", f"description={spec.description!r}"]
    if spec.params:
        params = ", ".join(_param_expr(param) for param in spec.params)
        kwargs.append(f"params=({params},)")
    if spec.inputs not in (0, 1) or spec.category != "source":
        if spec.category != "source":
            kwargs.append(f"inputs={spec.inputs!r}")
    if spec.outputs not in (0, 1) or spec.category != "sink":
        if spec.category != "sink":
            kwargs.append(f"outputs={spec.outputs!r}")
    if spec.stateful:
        kwargs.append("stateful=True")
    if not spec.mcu_supported:
        kwargs.append("mcu_supported=False")
    if not spec.host_supported:
        kwargs.append("host_supported=False")
    if spec.requires:
        kwargs.append(f"requires={tuple(spec.requires)!r}")
    if spec.tags:
        kwargs.append(f"tags={tuple(spec.tags)!r}")
    if spec.impl_key is not None:
        kwargs.append(f"impl_key={spec.impl_key!r}")
    return f"{cls_name}({', '.join(kwargs)})"


def generate_py() -> str:
    lines: list[str] = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from mara_host.tools.schema.control_graph\n")
    lines.append("from mara_host.tools.schema.control_graph.core import ParamDef, SinkDef, SourceDef, TransformDef\n")
    lines.append(f"SCHEMA_VERSION = {SCHEMA_VERSION}\n")
    lines.append(f"SOURCE_KINDS = {sorted(SOURCE_DEFS)!r}")
    lines.append(f"TRANSFORM_KINDS = {sorted(TRANSFORM_DEFS)!r}")
    lines.append(f"SINK_KINDS = {sorted(SINK_DEFS)!r}")
    lines.append(f"ALL_CONTROL_GRAPH_KINDS = {sorted(CONTROL_GRAPH_TYPES)!r}\n")
    lines.append("CONTROL_GRAPH_SPEC_OBJECTS = {")
    for name, spec in _sorted_dict(CONTROL_GRAPH_TYPES).items():
        lines.append(f"    {name!r}: {_graph_type_expr(spec)},")
    lines.append("}\n")
    lines.append(
        "CONTROL_GRAPH_SPECS = {name: spec.to_dict() for name, spec in CONTROL_GRAPH_SPEC_OBJECTS.items()}\n"
    )
    return "\n".join(lines)


def main() -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)

    JSON_OUT.write_text(generate_json(), encoding="utf-8")
    print(f"[gen_control_graph] Wrote {JSON_OUT}")

    PY_OUT.write_text(generate_py(), encoding="utf-8")
    print(f"[gen_control_graph] Wrote {PY_OUT}")

    GRAPH_JSON_SCHEMA_OUT.write_text(json.dumps(graph_json_schema(), indent=2), encoding="utf-8")
    print(f"[gen_control_graph] Wrote {GRAPH_JSON_SCHEMA_OUT}")


if __name__ == "__main__":
    main()
