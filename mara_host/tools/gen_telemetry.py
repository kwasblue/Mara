#!/usr/bin/env python3
"""
Generate telemetry section artifacts from platform_schema.TELEMETRY_SECTIONS.

Generates:
- C++ header: TelemetrySections.h (section IDs, format documentation)
- Python module: telemetry_sections.py (section ID constants)
"""

from pathlib import Path
from platform_schema import TELEMETRY_SECTIONS

# Output paths
CPP_OUT = Path("/Users/kwasiaddo/projects/PlatformIO/Projects/ESP32 MCU Host/include/telemetry/TelemetrySections.h")
PY_OUT = Path("/Users/kwasiaddo/projects/Host/mara_host/telemetry/telemetry_sections.py")


# -----------------------------------------------------------------------------
# C++ Generation
# -----------------------------------------------------------------------------

def generate_cpp_header() -> str:
    """Generate TelemetrySections.h content."""
    lines = []
    lines.append("// AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("// Generated from TELEMETRY_SECTIONS in platform_schema.py")
    lines.append("//")
    lines.append("// Binary telemetry section IDs for structured sensor data.")
    lines.append("// Use with registerBinProvider(section_id, ...) in TelemetryManager.")
    lines.append("")
    lines.append("#pragma once")
    lines.append("")
    lines.append("#include <cstdint>")
    lines.append("")
    lines.append("namespace TelemetrySections {")
    lines.append("")

    # Generate section ID constants
    lines.append("// Section IDs (must match Python telemetry_sections.py)")
    lines.append("enum class SectionId : uint8_t {")
    for name, spec in TELEMETRY_SECTIONS.items():
        section_id = spec["id"]
        desc = spec.get("description", "")
        lines.append(f"    {name.ljust(20)} = 0x{section_id:02X},  // {desc}")
    lines.append("};")
    lines.append("")

    # Generate helper to get section ID as uint8_t
    lines.append("// Helper to get section ID as raw byte")
    lines.append("inline uint8_t id(SectionId s) {")
    lines.append("    return static_cast<uint8_t>(s);")
    lines.append("}")
    lines.append("")

    # Generate format documentation as comments
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("// Section Formats (for reference)")
    lines.append("// All multi-byte values are little-endian")
    lines.append("// -----------------------------------------------------------------------------")
    lines.append("//")
    for name, spec in TELEMETRY_SECTIONS.items():
        fmt = spec.get("format", "")
        size = spec.get("size")
        size_str = f"{size} bytes" if size else "variable"
        lines.append(f"// {name}: {fmt}")
        lines.append(f"//   Size: {size_str}")
        lines.append("//")
    lines.append("")

    lines.append("} // namespace TelemetrySections")
    lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Python Generation
# -----------------------------------------------------------------------------

def generate_py_module() -> str:
    """Generate telemetry_sections.py content."""
    lines = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from TELEMETRY_SECTIONS in platform_schema.py")
    lines.append('"""')
    lines.append("Binary telemetry section IDs.")
    lines.append("")
    lines.append("These IDs must match the MCU's registerBinProvider() calls.")
    lines.append("All section parsers in binary_parser.py use these constants.")
    lines.append('"""')
    lines.append("")

    # Generate section ID constants
    lines.append("# Sensor telemetry sections")
    for name, spec in TELEMETRY_SECTIONS.items():
        if spec["id"] < 0x10:
            section_id = spec["id"]
            desc = spec.get("description", "")
            lines.append(f"{name.ljust(20)} = 0x{section_id:02X}  # {desc}")

    lines.append("")
    lines.append("# Control telemetry sections")
    for name, spec in TELEMETRY_SECTIONS.items():
        if spec["id"] >= 0x10:
            section_id = spec["id"]
            desc = spec.get("description", "")
            lines.append(f"{name.ljust(20)} = 0x{section_id:02X}  # {desc}")

    lines.append("")

    # Generate __all__
    lines.append("__all__ = [")
    for name in TELEMETRY_SECTIONS.keys():
        lines.append(f'    "{name}",')
    lines.append("]")
    lines.append("")

    # Generate section info dict for introspection
    lines.append("")
    lines.append("# Section metadata for introspection")
    lines.append("SECTION_INFO = {")
    for name, spec in TELEMETRY_SECTIONS.items():
        section_id = spec["id"]
        desc = spec.get("description", "")
        fmt = spec.get("format", "")
        size = spec.get("size")
        lines.append(f'    0x{section_id:02X}: {{')
        lines.append(f'        "name": "{name}",')
        lines.append(f'        "description": "{desc}",')
        lines.append(f'        "format": "{fmt}",')
        lines.append(f'        "size": {size if size else "None"},')
        lines.append(f'    }},')
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    print("[gen_telemetry] Generating telemetry section artifacts...")

    # Validate TELEMETRY_SECTIONS
    seen_ids = set()
    for name, spec in TELEMETRY_SECTIONS.items():
        section_id = spec.get("id")
        if section_id is None:
            raise ValueError(f"{name}: missing id")
        if section_id in seen_ids:
            raise ValueError(f"{name}: duplicate section id 0x{section_id:02X}")
        seen_ids.add(section_id)

    # Generate C++ header
    print(f"[gen_telemetry] Generating C++: {CPP_OUT}")
    cpp_code = generate_cpp_header()
    CPP_OUT.parent.mkdir(parents=True, exist_ok=True)
    CPP_OUT.write_text(cpp_code, encoding="utf-8")

    # Generate Python module
    print(f"[gen_telemetry] Generating Python: {PY_OUT}")
    py_code = generate_py_module()
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.write_text(py_code, encoding="utf-8")

    print("[gen_telemetry] Done.")


if __name__ == "__main__":
    main()
