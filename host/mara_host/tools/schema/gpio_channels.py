# schema/gpio_channels.py
"""GPIO logical channel definitions."""

from typing import Dict, List, Set

from .pins import PINS

# GPIO logical channels.
# pin_name must be a key in PINS.

GPIO_CHANNELS: List[Dict] = [
    {
        "name": "LED_STATUS",
        "channel": 0,
        "pin_name": "LED_STATUS",
        "mode": "output",
    },
    {
        "name": "ULTRASONIC_TRIG",
        "channel": 1,
        "pin_name": "ULTRA0_TRIG",
        "mode": "output",
    },
    {
        "name": "ULTRASONIC_ECHO",
        "channel": 2,
        "pin_name": "ULTRA0_ECHO",
        "mode": "input",
    },

    # --- DC motor direction pins (L298N Motor A) ---
    {
        "name": "MOTOR_LEFT_IN1",
        "channel": 3,
        "pin_name": "MOTOR_LEFT_IN1",
        "mode": "output",
    },
    {
        "name": "MOTOR_LEFT_IN2",
        "channel": 4,
        "pin_name": "MOTOR_LEFT_IN2",
        "mode": "output",
    },

    # --- Stepper enable (so host *can* poke EN if desired) ---
    {
        "name": "STEPPER0_EN",
        "channel": 5,
        "pin_name": "STEPPER0_EN",
        "mode": "output",
    },

    # --- Encoder pins exposed as GPIO inputs (for debug / GPIO_READ) ---
    {
        "name": "ENC0_A",
        "channel": 6,
        "pin_name": "ENC0_A",
        "mode": "input",
    },
    {
        "name": "ENC0_B",
        "channel": 7,
        "pin_name": "ENC0_B",
        "mode": "input",
    },
]


def validate_gpio_channels() -> None:
    """Validate GPIO_CHANNELS against PINS."""
    seen_channels: Set[int] = set()
    seen_names: Set[str] = set()

    for entry in GPIO_CHANNELS:
        name = entry["name"]
        ch = entry["channel"]
        pin_name = entry["pin_name"]
        mode = entry["mode"]

        if pin_name not in PINS:
            raise ValueError(f"GPIO_CHANNEL {name}: pin_name '{pin_name}' not in PINS")

        if mode not in ("output", "input", "input_pullup"):
            raise ValueError(
                f"{name}: mode must be 'output', 'input', or 'input_pullup'"
            )

        if ch in seen_channels:
            raise ValueError(f"Duplicate GPIO channel id {ch}")
        if name in seen_names:
            raise ValueError(f"Duplicate GPIO name {name}")

        seen_channels.add(ch)
        seen_names.add(name)


# Run validation at import time
validate_gpio_channels()
