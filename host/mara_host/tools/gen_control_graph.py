#!/usr/bin/env python3
"""Generate control-graph registry artifacts from the schema registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
HOST_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(HOST_DIR.parent))

from mara_host.tools.schema.control_graph import SOURCE_DEFS, TRANSFORM_DEFS, SINK_DEFS, CONTROL_GRAPH_TYPES
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


def generate_py() -> str:
    lines: list[str] = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from mara_host.tools.schema.control_graph\n")
    lines.append(f"SCHEMA_VERSION = {SCHEMA_VERSION}\n")
    lines.append(f"SOURCE_KINDS = {sorted(SOURCE_DEFS)!r}")
    lines.append(f"TRANSFORM_KINDS = {sorted(TRANSFORM_DEFS)!r}")
    lines.append(f"SINK_KINDS = {sorted(SINK_DEFS)!r}")
    lines.append(f"ALL_CONTROL_GRAPH_KINDS = {sorted(CONTROL_GRAPH_TYPES)!r}\n")
    lines.append(f"CONTROL_GRAPH_SPECS = { {name: spec.to_dict() for name, spec in _sorted_dict(CONTROL_GRAPH_TYPES).items()}!r }\n")
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
