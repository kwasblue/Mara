# mara_host/cli/cli_config.py
"""CLI configuration file support for MARA.

Reads defaults from ~/.mara.yaml or ~/.config/mara/config.yaml
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from mara_host.core._generated_config import DEFAULT_BAUD_RATE


# Config file locations (in order of precedence)
CONFIG_LOCATIONS = [
    Path.home() / ".mara.yaml",
    Path.home() / ".config" / "mara" / "config.yaml",
    Path.home() / ".config" / "mara.yaml",
]


_config_cache: Optional[dict] = None


def find_config_file() -> Optional[Path]:
    """Find the CLI config file."""
    for loc in CONFIG_LOCATIONS:
        if loc.exists():
            return loc
    return None


def load_config() -> dict:
    """Load CLI configuration from file.

    Returns empty dict if no config file exists.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_file = find_config_file()
    if config_file is None:
        _config_cache = {}
        return _config_cache

    try:
        with open(config_file) as f:
            _config_cache = yaml.safe_load(f) or {}
    except Exception:
        _config_cache = {}

    return _config_cache


def get(key: str, default: Any = None) -> Any:
    """Get a config value by dotted key path.

    Example:
        get("serial.port")  # Returns config["serial"]["port"]
        get("build.env", "esp32_usb")  # With default
    """
    config = load_config()

    # Navigate dotted path
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default

        if value is None:
            return default

    return value


def _platform_serial_default() -> str:
    """Return a sensible default serial port for the current OS."""
    import sys
    if sys.platform.startswith("linux"):
        return "/dev/ttyUSB0"
    elif sys.platform == "darwin":
        return "/dev/cu.usbserial-0001"
    else:
        return "COM3"


def get_serial_port() -> str:
    """Get default serial port (from config file, or platform default)."""
    return get("serial.port", _platform_serial_default())


def get_baudrate() -> int:
    """Get default baud rate."""
    return int(get("serial.baudrate", DEFAULT_BAUD_RATE))


def get_tcp_host() -> str:
    """Get default TCP host."""
    return get("tcp.host", "192.168.4.1")


def get_tcp_port() -> int:
    """Get default TCP port."""
    return int(get("tcp.port", 3333))


def get_tooling_backend() -> str:
    """Get default tooling backend (platformio, cmake, etc.)."""
    return get("tooling.backend", "platformio")


def get_tooling_environment() -> str:
    """Get default build environment/target."""
    return get("tooling.environment", "esp32_usb")


def get_tooling_preset() -> Optional[str]:
    """Get default feature preset."""
    return get("tooling.preset")


def get_robot_config_path() -> Optional[str]:
    """Get default robot YAML config path for config-aware service wiring."""
    return get("robot.config")


def create_default_config() -> str:
    """Generate default config file content."""
    return """# MARA CLI Configuration
# Save to ~/.mara.yaml

# Serial connection defaults
# Linux: /dev/ttyUSB0 or /dev/ttyACM0
# macOS: /dev/cu.usbserial-XXXX
# Windows: COM3
serial:
  # port: /dev/ttyUSB0  # Uncomment and set your port
  baudrate: 115200

# TCP/WiFi connection defaults
tcp:
  host: 192.168.4.1
  port: 3333

# Tooling configuration (build/flash/test)
tooling:
  # Backend: platformio, cmake, or other registered backends
  backend: platformio
  # Build environment/target
  environment: esp32_usb
  # Feature preset: minimal, motors, sensors, control, full
  # preset: motors

# CAN bus defaults
can:
  channel: can0
  bustype: socketcan
  node_id: 0

# Log directory
logs:
  directory: logs

# Editor for config files (optional)
# editor: code

# Theme (optional)
# theme: dark  # or 'light'
"""


def init_config(path: Optional[Path] = None) -> Path:
    """Create a default config file."""
    if path is None:
        path = CONFIG_LOCATIONS[0]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(create_default_config())

    return path


# Apply config defaults to argparse
def apply_defaults(parser_defaults: dict) -> dict:
    """Apply config file defaults to parser defaults.

    This is used to override argparse defaults with values from config file.
    """
    config = load_config()

    # Map config keys to argparse dest names
    mappings = {
        "serial.port": "port",
        "serial.baudrate": "baudrate",
        "tcp.host": "host",
        "tcp.port": "tcp_port",
        "tooling.backend": "backend",
        "tooling.environment": "env",
        "tooling.preset": "preset",
        "robot.config": "robot_config",
        "can.channel": "channel",
        "can.bustype": "bustype",
        "can.node_id": "node_id",
    }

    result = dict(parser_defaults)

    for config_key, arg_name in mappings.items():
        value = get(config_key)
        if value is not None:
            result[arg_name] = value

    return result
