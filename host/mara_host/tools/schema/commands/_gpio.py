# schema/commands/_gpio.py
"""LED, GPIO, and PWM command definitions."""

GPIO_COMMANDS: dict[str, dict] = {
    # LED
    "CMD_LED_ON": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Turn status LED on.",
        "payload": {},
    },

    "CMD_LED_OFF": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Turn status LED off.",
        "payload": {},
    },

    # GPIO
    "CMD_GPIO_WRITE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Write a digital value to a logical GPIO channel.",
        "payload": {
            "channel": {"type": "int", "required": True},
            "value": {"type": "int", "required": True},
        },
    },

    "CMD_GPIO_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Read a digital value from a logical GPIO channel.",
        "payload": {
            "channel": {"type": "int", "required": True},
        },
    },

    "CMD_GPIO_TOGGLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Toggle a logical GPIO channel.",
        "payload": {
            "channel": {"type": "int", "required": True},
        },
    },

    "CMD_GPIO_REGISTER_CHANNEL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Register or re-map a logical GPIO channel to a physical pin.",
        "payload": {
            "channel": {"type": "int", "required": True},
            "pin": {"type": "int", "required": True},
            "mode": {
                "type": "string",
                "required": False,
                "default": "output",
                "enum": ["output", "input", "input_pullup"],
            },
        },
    },

    # PWM
    "CMD_PWM_SET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set PWM duty cycle for a logical channel.",
        "payload": {
            "channel": {"type": "int", "required": True},
            "duty": {"type": "float", "required": True},
            "freq_hz": {"type": "float", "required": False},
        },
    },
}
