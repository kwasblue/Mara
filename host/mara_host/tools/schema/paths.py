# schema/paths.py
"""Output path constants for code generation."""

from pathlib import Path

# Root of the tools directory
ROOT = Path(__file__).resolve().parent.parent

# === OUTPUT PATHS (relative to monorepo structure) ===

# Python outputs (host/mara_host/...)
PY_CONFIG_DIR = ROOT.parent / "config"
PY_COMMAND_DIR = ROOT.parent / "command"
PY_TELEMETRY_DIR = ROOT.parent / "telemetry"
PY_TRANSPORT_DIR = ROOT.parent / "transport"

# Firmware outputs (firmware/mcu/include/...)
FIRMWARE_INCLUDE = ROOT.parent.parent.parent / "firmware" / "mcu" / "include"
CPP_CONFIG_DIR = FIRMWARE_INCLUDE / "config"
CPP_COMMAND_DIR = FIRMWARE_INCLUDE / "command"
CPP_TELEMETRY_DIR = FIRMWARE_INCLUDE / "telemetry"

# Location of pins.json (relative to this file)
PINS_JSON = ROOT.parent / "config" / "pins.json"
