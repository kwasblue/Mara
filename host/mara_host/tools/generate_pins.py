#!/usr/bin/env python3
"""
Generate PinConfig.h (C++) and pin_config.py (Python)
from PINS in platform_schema (which itself loads pins.json).
"""

from pathlib import Path
from platform_schema import ROOT, PINS, PINS_JSON, CPP_CONFIG_DIR, PY_CONFIG_DIR

# Where to write the C++ header (ESP32 firmware project)
CPP_OUT = CPP_CONFIG_DIR / "PinConfig.h"

# Where to write the python header (Host project)
PY_OUT = PY_CONFIG_DIR / "pin_config.py"


def generate_cpp(pins: dict) -> str:
    lines = []
    lines.append("// AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("// Generated from pins.json by gen_pins.py\n")
    lines.append("#pragma once")
    lines.append("#include <stdint.h>\n")
    lines.append("namespace Pins {")
    for name, value in sorted(pins.items()):
        lines.append(f"    constexpr uint8_t {name} = {value};")
    lines.append("} // namespace Pins")
    lines.append("")
    return "\n".join(lines)


def generate_py(pins: dict) -> str:
    lines = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from pins.json by gen_pins.py\n")
    for name, value in sorted(pins.items()):
        lines.append(f"{name} = {value}")
    lines.append("")
    return "\n".join(lines)


def main():
    print(f"[gen_pins] Using PINS from {PINS_JSON}")
    pins = PINS

    cpp_code = generate_cpp(pins)
    py_code = generate_py(pins)

    CPP_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)

    print(f"[gen_pins] Writing C++ header: {CPP_OUT}")
    CPP_OUT.write_text(cpp_code, encoding="utf-8")

    print(f"[gen_pins] Writing Python module: {PY_OUT}")
    PY_OUT.write_text(py_code, encoding="utf-8")

    print("[gen_pins] Done.")


if __name__ == "__main__":
    main()
