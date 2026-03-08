#!/usr/bin/env python3
"""
Generate GPIO channel mapping artifacts from schema.GPIO_CHANNELS.
"""

import json
from mara_host.tools.schema import GPIO_CHANNELS, PY_CONFIG_DIR, CPP_CONFIG_DIR

JSON_OUT = PY_CONFIG_DIR / "gpio_channels.json"
CPP_OUT = CPP_CONFIG_DIR / "GpioChannelDefs.h"
PY_OUT = PY_CONFIG_DIR / "gpio_channels.py"


def generate_json(channels: list[dict]) -> str:
    catalog = {
        "schema_version": 1,
        "gpio_channels": channels,
    }
    return json.dumps(catalog, indent=2, sort_keys=True)


def generate_cpp_header(channels: list[dict]) -> str:
    lines: list[str] = []
    lines.append("// AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("// Generated from GPIO_CHANNELS in schema.py\n")
    lines.append("#pragma once")
    lines.append("#include <Arduino.h>")
    lines.append("#include \"config/PinConfig.h\"\n")
    lines.append("struct GpioChannelDef {")
    lines.append("    int      channel;")
    lines.append("    uint8_t  pin;")
    lines.append("    uint8_t  mode;")
    lines.append("    const char* name;")
    lines.append("};\n")

    lines.append("constexpr GpioChannelDef GPIO_CHANNEL_DEFS[] = {")
    for entry in channels:
        name = entry["name"]
        ch   = entry["channel"]
        pin  = entry["pin_name"]
        mode = entry["mode"]

        if mode == "output":
            mode_expr = "OUTPUT"
        elif mode == "input":
            mode_expr = "INPUT"
        else:
            mode_expr = "INPUT_PULLUP"

        lines.append(
            f"    {{ {ch}, Pins::{pin}, {mode_expr}, \"{name}\" }},"
        )
    lines.append("};\n")
    lines.append(
        "constexpr size_t GPIO_CHANNEL_COUNT = sizeof(GPIO_CHANNEL_DEFS) / sizeof(GPIO_CHANNEL_DEFS[0]);\n"
    )

    return "\n".join(lines)


def generate_py_module(channels: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# AUTO-GENERATED FILE — DO NOT EDIT BY HAND")
    lines.append("# Generated from GPIO_CHANNELS in schema.py\n")

    lines.append("GPIO_CHANNELS = [")
    for entry in channels:
        name = entry["name"]
        ch   = entry["channel"]
        lines.append(f"    {{'name': '{name}', 'channel': {ch}}},")
    lines.append("]\n")

    for entry in channels:
        name = entry["name"]
        ch   = entry["channel"]
        const_name = "CH_" + name.upper()
        lines.append(f"{const_name} = {ch}")

    lines.append("")
    return "\n".join(lines)


def main():
    print("[gen_gpio_channels] Using GPIO_CHANNELS from schema.py")
    channels = GPIO_CHANNELS

    json_text = generate_json(channels)
    cpp_code  = generate_cpp_header(channels)
    py_code   = generate_py_module(channels)

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    CPP_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)

    print(f"[gen_gpio_channels] Writing JSON: {JSON_OUT}")
    JSON_OUT.write_text(json_text, encoding="utf-8")

    print(f"[gen_gpio_channels] Writing C++ header: {CPP_OUT}")
    CPP_OUT.write_text(cpp_code, encoding="utf-8")

    print(f"[gen_gpio_channels] Writing Python module: {PY_OUT}")
    PY_OUT.write_text(py_code, encoding="utf-8")

    print("[gen_gpio_channels] Done.")


if __name__ == "__main__":
    main()
