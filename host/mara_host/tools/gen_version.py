#!/usr/bin/env python3
"""
gen_version.py

Generates:
  - MCU:  include/config/Version.h
  - Host: mara_host/config/version.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]  # .../Host
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pathlib import Path
from mara_host.tools.platform_schema import VERSION


def generate_cpp_version(version: dict) -> str:
    """Generate C++ Version.h content."""
    return f'''// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from VERSION in platform_schema.py

#pragma once
#include <cstdint>

namespace Version {{
    constexpr const char* FIRMWARE = "{version["firmware"]}";
    constexpr uint8_t PROTOCOL = {version["protocol"]};
    constexpr const char* BOARD = "{version["board"]}";
    constexpr const char* NAME = "{version["name"]}";
}}
'''


def generate_py_version(version: dict) -> str:
    """Generate Python version.py content."""
    return f'''# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from VERSION in platform_schema.py

PROTOCOL_VERSION = {version["protocol"]}
CLIENT_VERSION = "{version["firmware"]}"
BOARD = "{version["board"]}"
NAME = "{version["name"]}"
'''


def write_version_files(version: dict, cpp_path: Path, py_path: Path) -> None:
    """Write version files for both firmware and host."""
    cpp_content = generate_cpp_version(version)
    cpp_path.parent.mkdir(parents=True, exist_ok=True)
    cpp_path.write_text(cpp_content)
    print(f"[gen_version] Wrote {cpp_path}")

    py_content = generate_py_version(version)
    py_path.parent.mkdir(parents=True, exist_ok=True)
    py_path.write_text(py_content)
    print(f"[gen_version] Wrote {py_path}")


def main() -> None:
    from platform_schema import CPP_CONFIG_DIR, PY_CONFIG_DIR

    cpp_path = CPP_CONFIG_DIR / "Version.h"
    py_path = PY_CONFIG_DIR / "version.py"

    write_version_files(VERSION, cpp_path, py_path)


if __name__ == "__main__":
    main()
