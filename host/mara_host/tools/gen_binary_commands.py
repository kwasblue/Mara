#!/usr/bin/env python3
"""
Generate binary command artifacts from schema.BINARY_COMMANDS.

Generates:
- C++ header: BinaryCommands.h (opcodes, structs, decode/encode functions)
- Python module: binary_commands.py (Opcode class, BinaryStreamer)
- Python module: json_to_binary.py (JSON-to-binary converter)
"""

from mara_host.tools.schema import BINARY_COMMANDS, CPP_COMMAND_DIR, PY_COMMAND_DIR

# Output paths
CPP_OUT = CPP_COMMAND_DIR / "BinaryCommands.h"
PY_BINARY_OUT = PY_COMMAND_DIR / "binary_commands.py"
PY_JSON_TO_BIN_OUT = PY_COMMAND_DIR / "json_to_binary.py"

# Type mappings
TYPE_MAP = {
    "u8": {"cpp": "uint8_t", "py_struct": "B", "size": 1},
    "u16": {"cpp": "uint16_t", "py_struct": "H", "size": 2},
    "u32": {"cpp": "uint32_t", "py_struct": "I", "size": 4},
    "i8": {"cpp": "int8_t", "py_struct": "b", "size": 1},
    "i16": {"cpp": "int16_t", "py_struct": "h", "size": 2},
    "i32": {"cpp": "int32_t", "py_struct": "i", "size": 4},
    "f32": {"cpp": "float", "py_struct": "f", "size": 4},
}


def to_pascal_case(name: str) -> str:
    """Convert UPPER_SNAKE to PascalCase: SET_VEL -> SetVel"""
    return "".join(word.capitalize() for word in name.split("_"))


def to_snake_case(name: str) -> str:
    """Convert UPPER_SNAKE to snake_case: SET_VEL -> set_vel"""
    return name.lower()


def get_struct_format(payload: list) -> str:
    """Get Python struct format string for payload."""
    fmt = "<B"  # Little-endian, opcode byte
    for field in payload:
        t = field["type"]
        if t not in TYPE_MAP:
            raise ValueError(f"Unknown type: {t}")
        fmt += TYPE_MAP[t]["py_struct"]
    return fmt


def get_payload_size(payload: list) -> int:
    """Calculate fixed payload size in bytes (excluding opcode)."""
    size = 0
    for field in payload:
        t = field["type"]
        if t not in TYPE_MAP:
            raise ValueError(f"Unknown type: {t}")
        size += TYPE_MAP[t]["size"]
    return size


# -----------------------------------------------------------------------------
# C++ Generation
# -----------------------------------------------------------------------------

def generate_cpp_header() -> str:
    """Generate BinaryCommands.h content."""
    lines = []
    lines.append("// AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("// Generated from BINARY_COMMANDS in schema.py")
    lines.append("//")
    lines.append("// Binary command protocol for high-rate streaming (10x smaller than JSON)")
    lines.append("//")
    lines.append("// Binary commands are compact fixed-format messages for control loops.")
    lines.append("// Use JSON commands for setup/config, binary for real-time streaming.")
    lines.append("")
    lines.append("#pragma once")
    lines.append("")
    lines.append("#include <cstdint>")
    lines.append("#include <cstring>")
    lines.append("")
    lines.append("namespace BinaryCommands {")
    lines.append("")

    # Generate Opcode enum
    lines.append("// Binary command opcodes")
    lines.append("enum class Opcode : uint8_t {")
    for name, spec in BINARY_COMMANDS.items():
        opcode = spec["opcode"]
        desc = spec.get("description", "")
        lines.append(f"    {name.ljust(15)} = 0x{opcode:02X},  // {desc}")
    lines.append("};")
    lines.append("")

    # Generate command structures
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("// Command Structures (POD types for union compatibility)")
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("")

    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        if not payload:
            continue  # No struct needed for commands without payload

        struct_name = f"{to_pascal_case(name)}Cmd"
        lines.append(f"struct {struct_name} {{")
        for field in payload:
            cpp_type = TYPE_MAP[field["type"]]["cpp"]
            lines.append(f"    {cpp_type} {field['name']};")
        lines.append("};")
        lines.append("")

    # Generate DecodeResult struct
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("// Decode Result")
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("")
    lines.append("struct DecodeResult {")
    lines.append("    Opcode opcode;")
    lines.append("    bool valid;")

    # Add union members for each command type with payload
    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        if payload:
            struct_name = f"{to_pascal_case(name)}Cmd"
            member_name = to_snake_case(name)
            lines.append(f"    {struct_name} {member_name};")

    lines.append("")
    lines.append("    DecodeResult() : opcode(Opcode::HEARTBEAT), valid(false) {")
    # Initialize all struct members
    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        if payload:
            member_name = to_snake_case(name)
            for field in payload:
                if field["type"] == "f32":
                    lines.append(f"        {member_name}.{field['name']} = 0.0f;")
                else:
                    lines.append(f"        {member_name}.{field['name']} = 0;")
    lines.append("    }")
    lines.append("};")
    lines.append("")

    # Generate helper functions
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("// Decode Functions")
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("")
    lines.append("// Helper to read little-endian values")
    lines.append("inline uint16_t read_u16_le(const uint8_t* buf) {")
    lines.append("    return static_cast<uint16_t>(buf[0]) | (static_cast<uint16_t>(buf[1]) << 8);")
    lines.append("}")
    lines.append("")
    lines.append("inline float read_f32_le(const uint8_t* buf) {")
    lines.append("    uint32_t v = static_cast<uint32_t>(buf[0])")
    lines.append("               | (static_cast<uint32_t>(buf[1]) << 8)")
    lines.append("               | (static_cast<uint32_t>(buf[2]) << 16)")
    lines.append("               | (static_cast<uint32_t>(buf[3]) << 24);")
    lines.append("    float f;")
    lines.append("    memcpy(&f, &v, sizeof(f));")
    lines.append("    return f;")
    lines.append("}")
    lines.append("")

    # Generate decode function
    lines.append("/**")
    lines.append(" * Decode a binary command packet")
    lines.append(" * @param data Pointer to command data (after opcode byte)")
    lines.append(" * @param len Length of data")
    lines.append(" * @param opcode Command opcode (first byte of packet)")
    lines.append(" * @return DecodeResult with parsed command")
    lines.append(" */")
    lines.append("inline DecodeResult decode(const uint8_t* data, size_t len, uint8_t opcode) {")
    lines.append("    DecodeResult result;")
    lines.append("    result.valid = false;")
    lines.append("")
    lines.append("    switch (static_cast<Opcode>(opcode)) {")

    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        is_variable = spec.get("variable_length", False)
        member_name = to_snake_case(name)
        payload_size = get_payload_size(payload)

        lines.append(f"    case Opcode::{name}:")

        if not payload:
            # No payload command
            lines.append(f"        result.opcode = Opcode::{name};")
            lines.append("        result.valid = true;")
        elif is_variable:
            # Variable-length command (like SET_SIGNALS)
            lines.append(f"        if (len >= {payload_size}) {{")
            lines.append(f"            result.opcode = Opcode::{name};")
            offset = 0
            for field in payload:
                t = field["type"]
                if t == "u8":
                    lines.append(f"            result.{member_name}.{field['name']} = data[{offset}];")
                elif t == "u16":
                    lines.append(f"            result.{member_name}.{field['name']} = read_u16_le(data + {offset});")
                elif t == "f32":
                    lines.append(f"            result.{member_name}.{field['name']} = read_f32_le(data + {offset});")
                offset += TYPE_MAP[t]["size"]

            # For SET_SIGNALS, validate we have enough data for all signals
            if name == "SET_SIGNALS":
                var_item = spec.get("variable_item", [])
                item_size = get_payload_size(var_item)
                lines.append(f"            // Validate we have enough data for all signals")
                lines.append(f"            size_t needed = {payload_size} + result.{member_name}.count * {item_size};")
                lines.append("            result.valid = (len >= needed);")
            else:
                lines.append("            result.valid = true;")
            lines.append("        }")
        else:
            # Fixed-length command
            lines.append(f"        if (len >= {payload_size}) {{")
            lines.append(f"            result.opcode = Opcode::{name};")
            offset = 0
            for field in payload:
                t = field["type"]
                if t == "u8":
                    lines.append(f"            result.{member_name}.{field['name']} = data[{offset}];")
                elif t == "u16":
                    lines.append(f"            result.{member_name}.{field['name']} = read_u16_le(data + {offset});")
                elif t == "f32":
                    lines.append(f"            result.{member_name}.{field['name']} = read_f32_le(data + {offset});")
                offset += TYPE_MAP[t]["size"]
            lines.append("            result.valid = true;")
            lines.append("        }")

        lines.append("        break;")
        lines.append("")

    lines.append("    default:")
    lines.append("        break;")
    lines.append("    }")
    lines.append("")
    lines.append("    return result;")
    lines.append("}")
    lines.append("")

    # Generate parseSignal helper for SET_SIGNALS
    lines.append("/**")
    lines.append(" * Parse individual signals from SET_SIGNALS command")
    lines.append(" * @param data Pointer to start of signal data (after count byte)")
    lines.append(" * @param index Signal index (0 to count-1)")
    lines.append(" * @param id_out Output signal ID")
    lines.append(" * @param value_out Output signal value")
    lines.append(" */")
    lines.append("inline void parseSignal(const uint8_t* data, uint8_t index, uint16_t& id_out, float& value_out) {")
    lines.append("    const uint8_t* ptr = data + (index * 6);")
    lines.append("    id_out = read_u16_le(ptr);")
    lines.append("    value_out = read_f32_le(ptr + 2);")
    lines.append("}")
    lines.append("")

    # Generate encode functions
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("// Encode Functions (for Python host reference)")
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("")

    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        is_variable = spec.get("variable_length", False)

        if is_variable:
            continue  # Skip variable-length encode for simplicity

        func_name = f"encode{to_pascal_case(name)}"

        if not payload:
            # No payload
            lines.append(f"/**")
            lines.append(f" * Encode {name} command (1 byte)")
            lines.append(f" */")
            lines.append(f"inline size_t {func_name}(uint8_t* buf) {{")
            lines.append(f"    buf[0] = static_cast<uint8_t>(Opcode::{name});")
            lines.append("    return 1;")
            lines.append("}")
        else:
            # With payload
            total_size = 1 + get_payload_size(payload)
            args = ", ".join(f"{TYPE_MAP[f['type']]['cpp']} {f['name']}" for f in payload)

            lines.append(f"/**")
            lines.append(f" * Encode {name} command")
            for f in payload:
                lines.append(f" * @param {f['name']} {f['name'].capitalize()}")
            lines.append(f" * @param buf Output buffer (must be at least {total_size} bytes)")
            lines.append(f" * @return Number of bytes written")
            lines.append(f" */")
            lines.append(f"inline size_t {func_name}({args}, uint8_t* buf) {{")
            lines.append(f"    buf[0] = static_cast<uint8_t>(Opcode::{name});")
            lines.append("")

            offset = 1
            for field in payload:
                t = field["type"]
                n = field["name"]
                if t == "u8":
                    lines.append(f"    buf[{offset}] = {n};")
                    offset += 1
                elif t == "u16":
                    lines.append(f"    buf[{offset}] = {n} & 0xFF;")
                    lines.append(f"    buf[{offset + 1}] = ({n} >> 8) & 0xFF;")
                    offset += 2
                elif t == "f32":
                    lines.append(f"    uint32_t v_{n};")
                    lines.append(f"    memcpy(&v_{n}, &{n}, sizeof(v_{n}));")
                    lines.append(f"    buf[{offset}] = v_{n} & 0xFF;")
                    lines.append(f"    buf[{offset + 1}] = (v_{n} >> 8) & 0xFF;")
                    lines.append(f"    buf[{offset + 2}] = (v_{n} >> 16) & 0xFF;")
                    lines.append(f"    buf[{offset + 3}] = (v_{n} >> 24) & 0xFF;")
                    offset += 4

            lines.append("")
            lines.append(f"    return {total_size};")
            lines.append("}")

        lines.append("")

    lines.append("} // namespace BinaryCommands")
    lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Python binary_commands.py Generation
# -----------------------------------------------------------------------------

def generate_py_binary_commands() -> str:
    """Generate binary_commands.py content."""
    lines = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from BINARY_COMMANDS in schema.py")
    lines.append('"""')
    lines.append("Binary command encoder for high-rate streaming.")
    lines.append("")
    lines.append("Use binary commands for real-time control loops (50+ Hz).")
    lines.append("Use JSON commands for setup/configuration.")
    lines.append("")
    lines.append("Binary format is ~10x smaller than equivalent JSON:")
    lines.append("  SET_VEL binary: 9 bytes")
    lines.append("  SET_VEL JSON:   ~50 bytes")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import struct")
    lines.append("from typing import List, Tuple")
    lines.append("")
    lines.append("")

    # Generate Opcode class
    lines.append("class Opcode:")
    lines.append('    """Binary command opcodes (must match BinaryCommands.h on MCU)."""')
    for name, spec in BINARY_COMMANDS.items():
        opcode = spec["opcode"]
        desc = spec.get("description", "")
        lines.append(f"    {name.ljust(15)} = 0x{opcode:02X}  # {desc}")
    lines.append("")
    lines.append("")

    # Generate BinaryStreamer class
    lines.append("class BinaryStreamer:")
    lines.append('    """')
    lines.append("    Encodes binary commands for high-rate streaming.")
    lines.append("")
    lines.append("    All multi-byte values are little-endian to match ESP32.")
    lines.append('    """')
    lines.append("")

    for name, spec in BINARY_COMMANDS.items():
        payload = spec.get("payload", [])
        is_variable = spec.get("variable_length", False)
        method_name = f"encode_{to_snake_case(name)}"
        desc = spec.get("description", name)

        if is_variable:
            # Special handling for SET_SIGNALS
            if name == "SET_SIGNALS":
                lines.append("    def encode_set_signals(self, signals: List[Tuple[int, float]]) -> bytes:")
                lines.append('        """')
                lines.append("        Encode SET_SIGNALS command for multiple signals.")
                lines.append("")
                lines.append("        Args:")
                lines.append("            signals: List of (signal_id, value) tuples")
                lines.append("")
                lines.append("        Returns:")
                lines.append("            Binary payload: opcode + count(u8) + [id(u16) + value(f32)] * count")
                lines.append('        """')
                lines.append("        count = min(len(signals), 255)  # Max 255 signals per packet")
                lines.append("        data = struct.pack('<BB', Opcode.SET_SIGNALS, count)")
                lines.append("        for i in range(count):")
                lines.append("            signal_id, value = signals[i]")
                lines.append("            data += struct.pack('<Hf', signal_id, value)")
                lines.append("        return data")
                lines.append("")
        elif not payload:
            # No payload command
            lines.append(f"    def {method_name}(self) -> bytes:")
            lines.append(f'        """{desc}"""')
            lines.append(f"        return struct.pack('<B', Opcode.{name})")
            lines.append("")
        else:
            # Fixed payload command
            args = ", ".join(f"{f['name']}: {'float' if f['type'] == 'f32' else 'int'}" for f in payload)
            fmt = get_struct_format(payload)
            pack_args = ", ".join(["Opcode." + name] + [f["name"] for f in payload])
            total_size = 1 + get_payload_size(payload)

            lines.append(f"    def {method_name}(self, {args}) -> bytes:")
            lines.append(f'        """')
            lines.append(f"        Encode {name} command.")
            lines.append("")
            lines.append("        Args:")
            for f in payload:
                lines.append(f"            {f['name']}: {f['name'].capitalize()}")
            lines.append("")
            lines.append("        Returns:")
            lines.append(f"            Binary payload ({total_size} bytes)")
            lines.append('        """')
            lines.append(f"        return struct.pack('{fmt}', {pack_args})")
            lines.append("")

    lines.append("")
    lines.append('__all__ = ["Opcode", "BinaryStreamer"]')
    lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Python json_to_binary.py Generation
# -----------------------------------------------------------------------------

def generate_py_json_to_binary() -> str:
    """Generate json_to_binary.py content."""
    lines = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from BINARY_COMMANDS in schema.py")
    lines.append('"""')
    lines.append("JSON-to-Binary command encoder.")
    lines.append("")
    lines.append("Converts JSON command dictionaries to compact binary format for wire transmission.")
    lines.append("The MCU receives binary (fast parsing) while the host writes JSON (human-readable).")
    lines.append("")
    lines.append("Example:")
    lines.append("    from mara_host.command.json_to_binary import JsonToBinaryEncoder")
    lines.append("    from mara_host.core.protocol import encode, MSG_CMD_BIN")
    lines.append("")
    lines.append("    encoder = JsonToBinaryEncoder()")
    lines.append("")
    lines.append("    # Write commands as JSON dicts")
    lines.append('    cmd = {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}')
    lines.append("")
    lines.append("    # Convert to binary")
    lines.append("    binary_payload = encoder.encode(cmd)")
    lines.append("    if binary_payload:")
    lines.append("        frame = encode(MSG_CMD_BIN, binary_payload)")
    lines.append("        transport.send(frame)")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import math")
    lines.append("import struct")
    lines.append("from typing import Dict, Any, Optional, List, Tuple")
    lines.append("")
    lines.append("from .binary_commands import Opcode")
    lines.append("")
    lines.append("")
    lines.append("def _validate_float(value: float, name: str) -> float:")
    lines.append('    """')
    lines.append("    Validate that a float value is finite (not NaN or Inf).")
    lines.append("")
    lines.append("    Raises ValueError if value is NaN or Inf, as these cannot be")
    lines.append("    safely packed into binary and may cause undefined MCU behavior.")
    lines.append('    """')
    lines.append("    if math.isnan(value) or math.isinf(value):")
    lines.append('        raise ValueError(f"{name} must be finite, got {value}")')
    lines.append("    return value")
    lines.append("")
    lines.append("")

    # Generate JsonToBinaryEncoder
    lines.append("class JsonToBinaryEncoder:")
    lines.append('    """')
    lines.append("    Converts JSON command dictionaries to binary wire format.")
    lines.append("")
    lines.append("    Supports a subset of commands that benefit from binary encoding:")
    lines.append("    - High-rate streaming commands (SET_VEL, SET_SIGNAL, etc.)")
    lines.append("    - Simple commands (HEARTBEAT, STOP)")
    lines.append("")
    lines.append("    Commands without binary support are returned as None (caller should")
    lines.append("    fall back to JSON encoding).")
    lines.append('    """')
    lines.append("")

    # Generate _COMMAND_MAP
    lines.append("    # Map JSON command types to binary opcodes (auto-generated)")
    lines.append("    _COMMAND_MAP: Dict[str, int] = {")
    for name, spec in BINARY_COMMANDS.items():
        json_cmd = spec.get("json_cmd")
        if json_cmd:
            lines.append(f'        "{json_cmd}": Opcode.{name},')
    lines.append("    }")
    lines.append("")

    # Generate encode method
    lines.append("    def encode(self, cmd: Dict[str, Any]) -> Optional[bytes]:")
    lines.append('        """')
    lines.append("        Encode a JSON command dict to binary.")
    lines.append("")
    lines.append("        Args:")
    lines.append('            cmd: JSON command dict with "type" field and payload fields.')
    lines.append('                 Example: {"type": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}')
    lines.append("")
    lines.append("        Returns:")
    lines.append("            Binary payload bytes, or None if command doesn't support binary.")
    lines.append('        """')
    lines.append('        cmd_type = cmd.get("type", "")')
    lines.append("")

    # Generate if-elif chain for each command with json_cmd
    first = True
    for name, spec in BINARY_COMMANDS.items():
        json_cmd = spec.get("json_cmd")
        if json_cmd:
            method_name = f"_encode_{to_snake_case(name)}"
            if first:
                lines.append(f'        if cmd_type == "{json_cmd}":')
                first = False
            else:
                lines.append(f'        elif cmd_type == "{json_cmd}":')
            lines.append(f"            return self.{method_name}(cmd)")

    lines.append("        else:")
    lines.append("            # No binary encoding for this command")
    lines.append("            return None")
    lines.append("")

    # Generate supports_binary method
    lines.append("    def supports_binary(self, cmd_type: str) -> bool:")
    lines.append('        """Check if a command type has binary encoding support."""')
    lines.append("        return cmd_type in self._COMMAND_MAP")
    lines.append("")

    # Generate encode methods for each command
    for name, spec in BINARY_COMMANDS.items():
        json_cmd = spec.get("json_cmd")
        if not json_cmd:
            continue

        payload = spec.get("payload", [])
        method_name = f"_encode_{to_snake_case(name)}"
        fmt = get_struct_format(payload)

        lines.append(f"    def {method_name}(self, cmd: Dict[str, Any]) -> bytes:")
        lines.append(f'        """')
        lines.append(f"        Encode {name} command.")
        lines.append("")
        lines.append(f"        JSON: {json_cmd}")
        lines.append(f'        """')

        if not payload:
            lines.append(f"        return struct.pack('<B', Opcode.{name})")
        else:
            for f in payload:
                default = "0.0" if f["type"] == "f32" else "0"
                if f["type"] == "f32":
                    # Validate float values to reject NaN/Inf before packing
                    lines.append(f"        {f['name']} = _validate_float(float(cmd.get(\"{f['name']}\", {default})), \"{f['name']}\")")
                else:
                    lines.append(f"        {f['name']} = int(cmd.get(\"{f['name']}\", {default}))")
            pack_args = ", ".join(["Opcode." + name] + [f["name"] for f in payload])
            lines.append(f"        return struct.pack('{fmt}', {pack_args})")

        lines.append("")

    # Generate JsonToBinaryBatchEncoder
    lines.append("")
    lines.append("class JsonToBinaryBatchEncoder(JsonToBinaryEncoder):")
    lines.append('    """')
    lines.append("    Extended encoder with batch signal support.")
    lines.append("")
    lines.append("    Use encode_signals() to batch multiple signal updates into one packet.")
    lines.append('    """')
    lines.append("")
    lines.append("    def encode_signals(self, signals: List[Tuple[int, float]]) -> bytes:")
    lines.append('        """')
    lines.append("        Encode multiple signals into one SET_SIGNALS command.")
    lines.append("")
    lines.append("        Args:")
    lines.append("            signals: List of (signal_id, value) tuples")
    lines.append("")
    lines.append("        Returns:")
    lines.append("            Binary payload: [opcode][count:u8][id:u16][value:f32]...")
    lines.append('        """')
    lines.append("        count = min(len(signals), 255)")
    lines.append("        data = struct.pack('<BB', Opcode.SET_SIGNALS, count)")
    lines.append("        for i in range(count):")
    lines.append("            signal_id, value = signals[i]")
    lines.append("            value = _validate_float(value, f'signal[{i}].value')")
    lines.append("            data += struct.pack('<Hf', signal_id, value)")
    lines.append("        return data")
    lines.append("")
    lines.append("    def encode_signal_cmds(self, cmds: List[Dict[str, Any]]) -> Optional[bytes]:")
    lines.append('        """')
    lines.append("        Batch multiple CMD_CTRL_SIGNAL_SET commands into one binary packet.")
    lines.append("")
    lines.append("        Args:")
    lines.append("            cmds: List of signal set commands")
    lines.append("")
    lines.append("        Returns:")
    lines.append("            Binary payload, or None if list is empty")
    lines.append('        """')
    lines.append("        signals = []")
    lines.append("        for cmd in cmds:")
    lines.append('            if cmd.get("type") == "CMD_CTRL_SIGNAL_SET":')
    lines.append('                signal_id = int(cmd.get("id", 0))')
    lines.append('                value = float(cmd.get("value", 0.0))')
    lines.append("                signals.append((signal_id, value))")
    lines.append("")
    lines.append("        if not signals:")
    lines.append("            return None")
    lines.append("")
    lines.append("        return self.encode_signals(signals)")
    lines.append("")
    lines.append("")
    lines.append('__all__ = ["JsonToBinaryEncoder", "JsonToBinaryBatchEncoder"]')
    lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    print("[gen_binary_commands] Generating binary command artifacts...")

    # Validate BINARY_COMMANDS
    seen_opcodes = set()
    for name, spec in BINARY_COMMANDS.items():
        opcode = spec.get("opcode")
        if opcode is None:
            raise ValueError(f"{name}: missing opcode")
        if opcode in seen_opcodes:
            raise ValueError(f"{name}: duplicate opcode 0x{opcode:02X}")
        seen_opcodes.add(opcode)

        for field in spec.get("payload", []):
            if field["type"] not in TYPE_MAP:
                raise ValueError(f"{name}.{field['name']}: unknown type {field['type']}")

    # Generate C++ header
    print(f"[gen_binary_commands] Generating C++: {CPP_OUT}")
    cpp_code = generate_cpp_header()
    CPP_OUT.parent.mkdir(parents=True, exist_ok=True)
    CPP_OUT.write_text(cpp_code, encoding="utf-8")

    # Generate Python binary_commands.py
    print(f"[gen_binary_commands] Generating Python: {PY_BINARY_OUT}")
    py_binary_code = generate_py_binary_commands()
    PY_BINARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_BINARY_OUT.write_text(py_binary_code, encoding="utf-8")

    # Generate Python json_to_binary.py
    print(f"[gen_binary_commands] Generating Python: {PY_JSON_TO_BIN_OUT}")
    py_json_to_bin_code = generate_py_json_to_binary()
    PY_JSON_TO_BIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_JSON_TO_BIN_OUT.write_text(py_json_to_bin_code, encoding="utf-8")

    print("[gen_binary_commands] Done.")


if __name__ == "__main__":
    main()
