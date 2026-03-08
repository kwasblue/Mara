#!/usr/bin/env python3
"""
Generate CAN bus message definitions from schema.

This generator creates:
    - C++ CanDefs.h for MCU firmware
    - Python can_defs.py for host (validates against schema)

The generated code provides:
    - Message ID constants
    - Packed struct definitions
    - Encode/decode functions
    - Node state enum

Usage:
    python -m mara_host.tools.gen_can
"""

from typing import Dict, List

from mara_host.tools.schema import (
    CAN_CONFIG,
    CAN_MESSAGE_IDS,
    CAN_MESSAGES,
    CAN_NODE_STATES,
    CPP_CONFIG_DIR,
    PY_TRANSPORT_DIR,
)

# Output paths
CPP_OUT = CPP_CONFIG_DIR / "CanDefs.h"
PY_OUT = PY_TRANSPORT_DIR / "can_defs_generated.py"


# =============================================================================
# TYPE MAPPING
# =============================================================================

TYPE_TO_CPP = {
    "u8": "uint8_t",
    "i8": "int8_t",
    "u16": "uint16_t",
    "i16": "int16_t",
    "u32": "uint32_t",
    "i32": "int32_t",
    "f32": "float",
}

TYPE_TO_STRUCT_FMT = {
    "u8": "B",
    "i8": "b",
    "u16": "H",
    "i16": "h",
    "u32": "I",
    "i32": "i",
    "f32": "f",
}

TYPE_SIZES = {
    "u8": 1,
    "i8": 1,
    "u16": 2,
    "i16": 2,
    "u32": 4,
    "i32": 4,
    "f32": 4,
}


def calc_struct_size(fields: List[Dict]) -> int:
    """Calculate total struct size in bytes."""
    return sum(TYPE_SIZES[f["type"]] for f in fields)


def build_struct_fmt(fields: List[Dict]) -> str:
    """Build Python struct format string (little-endian)."""
    return "<" + "".join(TYPE_TO_STRUCT_FMT[f["type"]] for f in fields)


# =============================================================================
# C++ GENERATION
# =============================================================================

def generate_cpp_header() -> str:
    """Generate C++ CanDefs.h content."""
    lines = [
        "// AUTO-GENERATED FILE — DO NOT EDIT BY HAND",
        "// Generated from CAN_MESSAGES in schema.py",
        "//",
        "// CAN bus message definitions for hybrid real-time/protocol transport.",
        "",
        "#pragma once",
        "",
        "#include <cstdint>",
        "#include <cstring>",
        "",
        "namespace can {",
        "",
    ]

    # Configuration
    lines.extend([
        "// =============================================================================",
        "// CONFIGURATION",
        "// =============================================================================",
        "",
        f"constexpr uint8_t MAX_NODE_ID = {CAN_CONFIG['max_node_id']};",
        f"constexpr uint8_t BROADCAST_ID = 0x{CAN_CONFIG['broadcast_id']:02X};",
        f"constexpr uint32_t DEFAULT_BAUD_RATE = {CAN_CONFIG['default_baud_rate']};",
        f"constexpr size_t PROTO_PAYLOAD_SIZE = {CAN_CONFIG['proto_payload_size']};",
        f"constexpr size_t PROTO_MAX_FRAMES = {CAN_CONFIG['proto_max_frames']};",
        f"constexpr size_t PROTO_MAX_MSG_SIZE = {CAN_CONFIG['proto_max_msg_size']};",
        "",
    ])

    # Message IDs
    lines.extend([
        "// =============================================================================",
        "// MESSAGE IDS",
        "// =============================================================================",
        "",
        "namespace MsgId {",
    ])
    for name, value in CAN_MESSAGE_IDS.items():
        lines.append(f"    constexpr uint16_t {name} = 0x{value:03X};")
    lines.extend(["}", ""])

    # Helper functions
    lines.extend([
        "// Helper to build message ID with node",
        "inline constexpr uint16_t makeId(uint16_t base, uint8_t nodeId) {",
        "    return base | (nodeId & 0x0F);",
        "}",
        "",
        "// Extract node ID from message ID",
        "inline constexpr uint8_t extractNodeId(uint16_t msgId) {",
        "    return msgId & 0x0F;",
        "}",
        "",
    ])

    # Node state enum
    lines.extend([
        "// =============================================================================",
        "// NODE STATE ENUM",
        "// =============================================================================",
        "",
        "enum class NodeState : uint8_t {",
    ])
    for name, value in CAN_NODE_STATES.items():
        lines.append(f"    {name} = {value},")
    lines.extend(["};", ""])

    # Packed structures
    lines.extend([
        "// =============================================================================",
        "// PACKED MESSAGE STRUCTURES",
        "// =============================================================================",
        "",
        "#pragma pack(push, 1)",
        "",
    ])

    for msg_name, msg_spec in CAN_MESSAGES.items():
        struct_name = f"{msg_name.title().replace('_', '')}Msg"
        fields = msg_spec.get("struct", [])
        description = msg_spec.get("description", "")
        size = calc_struct_size(fields)

        lines.append(f"// {description}")
        lines.append(f"struct {struct_name} {{")
        for field in fields:
            cpp_type = TYPE_TO_CPP[field["type"]]
            field_name = field["name"]
            unit = field.get("unit", "")
            comment = f"  // {unit}" if unit else ""
            lines.append(f"    {cpp_type} {field_name};{comment}")
        lines.append("};")
        lines.append(f"static_assert(sizeof({struct_name}) == {size}, \"{struct_name} size mismatch\");")
        lines.append("")

    lines.extend([
        "#pragma pack(pop)",
        "",
        "} // namespace can",
        "",
    ])

    return "\n".join(lines)


# =============================================================================
# PYTHON GENERATION
# =============================================================================

def generate_python_module() -> str:
    """Generate Python can_defs_generated.py content."""
    lines = [
        "# AUTO-GENERATED FILE — DO NOT EDIT BY HAND",
        "# Generated from CAN_MESSAGES in schema.py",
        "#",
        "# This file validates that can_defs.py matches the schema.",
        "# Import can_defs.py directly for runtime use.",
        "",
        "from __future__ import annotations",
        "",
        "import struct",
        "from dataclasses import dataclass",
        "from enum import IntEnum",
        "from typing import Tuple",
        "",
    ]

    # Configuration
    lines.extend([
        "# Configuration",
        f"MAX_NODE_ID = {CAN_CONFIG['max_node_id']}",
        f"BROADCAST_ID = 0x{CAN_CONFIG['broadcast_id']:02X}",
        f"DEFAULT_BAUD_RATE = {CAN_CONFIG['default_baud_rate']}",
        f"PROTO_PAYLOAD_SIZE = {CAN_CONFIG['proto_payload_size']}",
        f"PROTO_MAX_FRAMES = {CAN_CONFIG['proto_max_frames']}",
        f"PROTO_MAX_MSG_SIZE = {CAN_CONFIG['proto_max_msg_size']}",
        "",
    ])

    # Message IDs
    lines.extend([
        "# Message IDs",
        "class MsgId:",
    ])
    for name, value in CAN_MESSAGE_IDS.items():
        lines.append(f"    {name} = 0x{value:03X}")
    lines.append("")

    # Node state enum
    lines.extend([
        "# Node state enum",
        "class NodeState(IntEnum):",
    ])
    for name, value in CAN_NODE_STATES.items():
        lines.append(f"    {name} = {value}")
    lines.append("")

    # Message structures
    for msg_name, msg_spec in CAN_MESSAGES.items():
        class_name = f"{msg_name.title().replace('_', '')}Msg"
        fields = msg_spec.get("struct", [])
        description = msg_spec.get("description", "")
        struct_fmt = build_struct_fmt(fields)

        lines.append(f"# {description}")
        lines.append("@dataclass")
        lines.append(f"class {class_name}:")

        for field in fields:
            field_name = field["name"]
            field_type = "int" if field["type"] != "f32" else "float"
            lines.append(f"    {field_name}: {field_type}")

        lines.append(f'    STRUCT_FMT = "{struct_fmt}"')
        lines.append("")

        # Pack method
        field_names = ", ".join(f"self.{f['name']}" for f in fields)
        lines.append("    def pack(self) -> bytes:")
        lines.append(f"        return struct.pack(self.STRUCT_FMT, {field_names})")
        lines.append("")

        # Unpack method
        field_list = ", ".join(f["name"] for f in fields)
        lines.append("    @classmethod")
        lines.append(f'    def unpack(cls, data: bytes) -> "{class_name}":')
        lines.append(f"        {field_list} = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])")
        lines.append(f"        return cls({field_list})")
        lines.append("")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Generate CAN definition files."""
    print("[gen_can] Generating CAN definitions from schema...")

    # Generate C++ header
    print(f"[gen_can] Generating C++ header: {CPP_OUT}")
    cpp_code = generate_cpp_header()
    CPP_OUT.parent.mkdir(parents=True, exist_ok=True)
    CPP_OUT.write_text(cpp_code, encoding="utf-8")

    # Generate Python module
    print(f"[gen_can] Generating Python module: {PY_OUT}")
    py_code = generate_python_module()
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.write_text(py_code, encoding="utf-8")

    print("[gen_can] Done.")

    # Print summary
    print(f"\n[gen_can] Summary:")
    print(f"  Message IDs: {len(CAN_MESSAGE_IDS)}")
    print(f"  Message structs: {len(CAN_MESSAGES)}")
    print(f"  Node states: {len(CAN_NODE_STATES)}")


if __name__ == "__main__":
    main()
