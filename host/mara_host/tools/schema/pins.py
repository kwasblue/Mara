# schema/pins.py
"""Pin configuration loading from pins.json."""

import json
from pathlib import Path
from typing import Dict

from .paths import PINS_JSON


def _load_pins(path: Path) -> Dict[str, int]:
    """Load and validate pins from JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("pins.json must be a JSON object {NAME: number, ...}")

    for name, value in data.items():
        if not isinstance(name, str):
            raise ValueError(f"Pin name {name!r} is not a string")
        if not isinstance(value, int):
            raise ValueError(f"Pin {name} value {value!r} is not an int")
        if not (0 <= value <= 39):
            raise ValueError(f"Pin {name} value {value} looks invalid for ESP32 GPIO")

    return data


# Load pins at import time
PINS: Dict[str, int] = _load_pins(PINS_JSON)
