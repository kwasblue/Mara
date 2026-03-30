#!/usr/bin/env python3
"""Generate typed Python classes for control graph nodes from schema definitions.

This generates classes that provide a clean API for building control graphs
without nested dicts. The generated classes have IDE autocomplete and type hints.

Usage:
    python -m mara_host.tools.gen_control_graph_types

Output:
    mara_host/control_graph/nodes.py
"""

from __future__ import annotations

from pathlib import Path

from mara_host.tools.schema.control_graph import SOURCE_DEFS, TRANSFORM_DEFS, SINK_DEFS
from mara_host.tools.schema.control_graph.core import GraphTypeDef, ParamDef
from mara_host.tools.schema.control_graph.schema import GRAPH_SCHEMA_VERSION


def param_to_python_type(param: ParamDef) -> str:
    """Convert schema param type to Python type hint."""
    type_map = {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "enum": "str",
        "string_list": "list[str]",
    }
    return type_map.get(param.type, "Any")


def param_default_repr(param: ParamDef) -> str:
    """Get Python repr of default value."""
    if param.default is None:
        return "None"
    if isinstance(param.default, str):
        return repr(param.default)
    if isinstance(param.default, bool):
        return "True" if param.default else "False"
    if isinstance(param.default, list):
        return repr(param.default)
    return str(param.default)


def to_class_name(kind: str) -> str:
    """Convert kind to PascalCase class name."""
    # signal_read -> SignalRead
    # encoder_velocity -> EncoderVelocity
    return "".join(word.capitalize() for word in kind.split("_"))


def generate_node_class(spec: GraphTypeDef, category: str) -> str:
    """Generate a single node class."""
    class_name = to_class_name(spec.kind)

    # Build __init__ params
    init_params = []
    init_body = []
    to_dict_params = []

    for param in spec.params:
        py_type = param_to_python_type(param)

        if param.required and param.default is None:
            # Required param, no default
            init_params.append(f"{param.name}: {py_type}")
        else:
            # Optional param with default
            default = param_default_repr(param)
            init_params.append(f"{param.name}: {py_type} = {default}")

        init_body.append(f"self.{param.name} = {param.name}")
        to_dict_params.append(f'"{param.name}": self.{param.name}')

    # Handle no params case
    if not init_params:
        init_params_str = "self"
        init_body_str = "pass"
    else:
        init_params_str = "self, " + ", ".join(init_params)
        init_body_str = "\n        ".join(init_body)

    if to_dict_params:
        params_dict = "{\n            " + ",\n            ".join(to_dict_params) + "\n        }"
    else:
        params_dict = "{}"

    docstring = spec.description or f"{class_name} {category}."

    return f'''
class {class_name}:
    """{docstring}"""
    _kind = "{spec.kind}"
    _category = "{category}"

    def __init__({init_params_str}):
        {init_body_str}

    def to_dict(self) -> dict:
        return {{"type": self._kind, "params": {params_dict}}}

    def __repr__(self) -> str:
        return f"{class_name}(...)"
'''


def generate_all() -> str:
    """Generate the complete nodes module."""

    lines = [
        '"""',
        'AUTO-GENERATED FILE - DO NOT EDIT',
        '',
        'Generated from mara_host.tools.schema.control_graph definitions.',
        'Run: python -m mara_host.tools.gen_control_graph_types',
        '"""',
        '',
        'from __future__ import annotations',
        'from typing import Any',
        '',
        f'SCHEMA_VERSION = {GRAPH_SCHEMA_VERSION}',
        '',
        '',
        '# =============================================================================',
        '# Sources',
        '# =============================================================================',
    ]

    source_classes = []
    for kind, spec in sorted(SOURCE_DEFS.items()):
        lines.append(generate_node_class(spec, "source"))
        source_classes.append(to_class_name(kind))

    lines.append('')
    lines.append('# =============================================================================')
    lines.append('# Transforms')
    lines.append('# =============================================================================')

    transform_classes = []
    for kind, spec in sorted(TRANSFORM_DEFS.items()):
        lines.append(generate_node_class(spec, "transform"))
        transform_classes.append(to_class_name(kind))

    lines.append('')
    lines.append('# =============================================================================')
    lines.append('# Sinks')
    lines.append('# =============================================================================')

    sink_classes = []
    for kind, spec in sorted(SINK_DEFS.items()):
        lines.append(generate_node_class(spec, "sink"))
        sink_classes.append(to_class_name(kind))

    # Add Slot and Graph classes
    lines.append('''
# =============================================================================
# Graph Structure
# =============================================================================

class Slot:
    """A control graph slot with source, transforms, and sink(s)."""

    def __init__(
        self,
        id: str,
        source,
        sink = None,
        sinks: list | None = None,
        transforms: list | None = None,
        rate_hz: int | None = None,
        enabled: bool = True,
    ):
        self.id = id
        self.source = source
        self.sink = sink
        self.sinks = sinks or []
        self.transforms = transforms or []
        self.rate_hz = rate_hz
        self.enabled = enabled

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "enabled": self.enabled,
            "source": self.source.to_dict(),
            "transforms": [t.to_dict() for t in self.transforms],
        }
        if self.rate_hz is not None:
            d["rate_hz"] = self.rate_hz
        if self.sink is not None:
            d["sink"] = self.sink.to_dict()
        elif self.sinks:
            d["sinks"] = [s.to_dict() for s in self.sinks]
        return d

    def __repr__(self) -> str:
        return f"Slot({self.id!r}, ...)"


class Graph:
    """A complete control graph configuration."""

    def __init__(self, slots: list[Slot]):
        self.slots = slots
        self.schema_version = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "slots": [s.to_dict() for s in self.slots],
        }

    def __repr__(self) -> str:
        return f"Graph({len(self.slots)} slots)"


# =============================================================================
# Exports
# =============================================================================

SOURCES = [
''')

    for cls in source_classes:
        lines.append(f'    "{cls}",')
    lines.append(']')

    lines.append('')
    lines.append('TRANSFORMS = [')
    for cls in transform_classes:
        lines.append(f'    "{cls}",')
    lines.append(']')

    lines.append('')
    lines.append('SINKS = [')
    for cls in sink_classes:
        lines.append(f'    "{cls}",')
    lines.append(']')

    lines.append('')
    lines.append('__all__ = [')
    lines.append('    "Graph",')
    lines.append('    "Slot",')
    lines.append('    "SCHEMA_VERSION",')
    for cls in source_classes + transform_classes + sink_classes:
        lines.append(f'    "{cls}",')
    lines.append(']')

    return "\n".join(lines)


def main():
    # Output path
    output_dir = Path(__file__).parent.parent / "control_graph"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "nodes.py"

    content = generate_all()

    output_file.write_text(content)
    print(f"Generated: {output_file}")

    # Also create __init__.py if it doesn't exist
    init_file = output_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Control graph building utilities."""\n\nfrom .nodes import *\n')
        print(f"Generated: {init_file}")


if __name__ == "__main__":
    main()
