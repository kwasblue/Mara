#!/usr/bin/env python3
"""Generate typed Python dataclasses for command payloads from schema definitions.

This generates dataclasses that provide a clean API for building command payloads
with IDE autocomplete and type hints.

Usage:
    python -m mara_host.tools.gen_command_payloads

Output:
    mara_host/command/payloads.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from mara_host.tools.schema.commands import COMMAND_OBJECTS
from mara_host.tools.schema.commands.core import CommandDef, FieldDef, UNSET


def field_to_python_type(fdef: FieldDef | dict) -> str:
    """Convert schema field type to Python type hint."""
    if isinstance(fdef, dict):
        type_str = fdef.get("type", "any")
    else:
        type_str = fdef.type

    type_map = {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "array": "list",
        "object": "dict[str, Any]",
    }
    return type_map.get(type_str, "Any")


def field_default_repr(fdef: FieldDef | dict) -> str:
    """Get Python repr of default value."""
    if isinstance(fdef, dict):
        default = fdef.get("default", UNSET)
        required = fdef.get("required", False)
    else:
        default = fdef.default
        required = fdef.required

    if required and default is UNSET:
        return None  # No default, required field
    if default is UNSET:
        return "None"
    if isinstance(default, str):
        return repr(default)
    if isinstance(default, bool):
        return "True" if default else "False"
    if isinstance(default, list):
        return repr(default)
    return str(default)


def cmd_name_to_class_name(cmd_name: str) -> str:
    """Convert CMD_DC_SET_SPEED to DcSetSpeedPayload."""
    # Remove CMD_ prefix
    name = cmd_name
    if name.startswith("CMD_"):
        name = name[4:]

    # Convert SNAKE_CASE to PascalCase
    parts = name.split("_")
    pascal = "".join(part.capitalize() for part in parts)
    return f"{pascal}Payload"


def generate_payload_class(cmd_name: str, cmd_def: CommandDef) -> str:
    """Generate a single payload dataclass."""
    class_name = cmd_name_to_class_name(cmd_name)

    # Separate required and optional fields
    required_params = []
    optional_params = []
    to_dict_fields = []

    for field_name, field_def in cmd_def.payload.items():
        if isinstance(field_def, dict):
            fdef = FieldDef(**field_def) if "type" in field_def else None
            if fdef is None:
                continue
        else:
            fdef = field_def

        py_type = field_to_python_type(fdef)
        default = field_default_repr(fdef)

        if default is None:
            # Required field
            required_params.append((field_name, py_type, None))
        else:
            # Optional field
            optional_params.append((field_name, py_type, default))

        to_dict_fields.append(field_name)

    # Build __init__ signature - required params first, then optional
    init_params = []
    init_body = []

    for field_name, py_type, _ in required_params:
        init_params.append(f"{field_name}: {py_type}")
        init_body.append(f"self.{field_name} = {field_name}")

    for field_name, py_type, default in optional_params:
        if default == "None":
            init_params.append(f"{field_name}: {py_type} | None = {default}")
        else:
            init_params.append(f"{field_name}: {py_type} = {default}")
        init_body.append(f"self.{field_name} = {field_name}")

    # Handle no params case
    if not init_params:
        init_params_str = "self"
        init_body_str = "pass"
    else:
        init_params_str = "self, " + ", ".join(init_params)
        init_body_str = "\n        ".join(init_body) if init_body else "pass"

    # Build to_dict body
    if to_dict_fields:
        to_dict_items = ",\n            ".join(f'"{f}": self.{f}' for f in to_dict_fields)
        to_dict_body = f"return {{\n            {to_dict_items}\n        }}"
    else:
        to_dict_body = "return {}"

    docstring = cmd_def.description or f"Payload for {cmd_name}."

    return f'''
class {class_name}:
    """{docstring}"""
    _cmd = "{cmd_name}"

    def __init__({init_params_str}):
        {init_body_str}

    def to_dict(self) -> dict[str, Any]:
        {to_dict_body}

    def __repr__(self) -> str:
        return f"{class_name}(...)"
'''


def generate_all() -> str:
    """Generate the complete payloads module."""

    lines = [
        '"""',
        'AUTO-GENERATED FILE - DO NOT EDIT',
        '',
        'Generated from mara_host.tools.schema.commands definitions.',
        'Run: python -m mara_host.tools.gen_command_payloads',
        '"""',
        '',
        'from __future__ import annotations',
        'from typing import Any',
        '',
    ]

    # Group commands by category
    categories = {
        "safety": [],
        "control": [],
        "motion": [],
        "servo": [],
        "dc_motor": [],
        "stepper": [],
        "gpio": [],
        "sensors": [],
        "telemetry": [],
        "wifi": [],
        "camera": [],
        "other": [],
    }

    for cmd_name, cmd_def in sorted(COMMAND_OBJECTS.items()):
        # Only generate for host->mcu commands with payloads
        if cmd_def.direction != "host->mcu":
            continue
        if not cmd_def.payload:
            continue

        # Categorize
        lower_name = cmd_name.lower()
        if "arm" in lower_name or "estop" in lower_name or "stop" in lower_name or "safety" in lower_name:
            categories["safety"].append((cmd_name, cmd_def))
        elif "servo" in lower_name:
            categories["servo"].append((cmd_name, cmd_def))
        elif "dc" in lower_name:
            categories["dc_motor"].append((cmd_name, cmd_def))
        elif "stepper" in lower_name:
            categories["stepper"].append((cmd_name, cmd_def))
        elif "gpio" in lower_name:
            categories["gpio"].append((cmd_name, cmd_def))
        elif "vel" in lower_name or "motion" in lower_name:
            categories["motion"].append((cmd_name, cmd_def))
        elif "telemetry" in lower_name or "observer" in lower_name:
            categories["telemetry"].append((cmd_name, cmd_def))
        elif "wifi" in lower_name:
            categories["wifi"].append((cmd_name, cmd_def))
        elif "camera" in lower_name:
            categories["camera"].append((cmd_name, cmd_def))
        elif "imu" in lower_name or "sensor" in lower_name or "encoder" in lower_name:
            categories["sensors"].append((cmd_name, cmd_def))
        else:
            categories["other"].append((cmd_name, cmd_def))

    class_names = []

    for category, commands in categories.items():
        if not commands:
            continue

        lines.append('')
        lines.append('# =============================================================================')
        lines.append(f'# {category.replace("_", " ").title()} Commands')
        lines.append('# =============================================================================')

        for cmd_name, cmd_def in commands:
            try:
                class_code = generate_payload_class(cmd_name, cmd_def)
                lines.append(class_code)
                class_names.append(cmd_name_to_class_name(cmd_name))
            except Exception as e:
                lines.append(f'# Skipped {cmd_name}: {e}')

    # Add __all__
    lines.append('')
    lines.append('# =============================================================================')
    lines.append('# Exports')
    lines.append('# =============================================================================')
    lines.append('')
    lines.append('__all__ = [')
    for name in sorted(class_names):
        lines.append(f'    "{name}",')
    lines.append(']')

    return "\n".join(lines)


def main():
    # Output path
    output_dir = Path(__file__).parent.parent / "command"
    output_file = output_dir / "payloads.py"

    content = generate_all()

    output_file.write_text(content)
    print(f"Generated: {output_file}")


if __name__ == "__main__":
    main()
