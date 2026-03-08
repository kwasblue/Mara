# schema/commands/_observer.py
"""Observer command definitions."""

OBSERVER_COMMANDS: dict[str, dict] = {
    "CMD_OBSERVER_CONFIG": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Configure a Luenberger state observer.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
                "description": "Observer slot index (0-3).",
            },
            "num_states": {
                "type": "int",
                "required": True,
                "min": 1,
                "max": 6,
                "description": "Number of states to estimate.",
            },
            "num_inputs": {
                "type": "int",
                "required": False,
                "default": 1,
                "min": 1,
                "max": 2,
                "description": "Number of control inputs (u).",
            },
            "num_outputs": {
                "type": "int",
                "required": True,
                "min": 1,
                "max": 4,
                "description": "Number of measurements (y).",
            },
            "rate_hz": {
                "type": "int",
                "required": False,
                "default": 200,
                "min": 50,
                "max": 1000,
                "description": "Observer update rate in Hz.",
            },
            "input_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": True,
                "description": "Signal IDs for control inputs (u).",
            },
            "output_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": True,
                "description": "Signal IDs for measurements (y).",
            },
            "estimate_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": True,
                "description": "Signal IDs where state estimates (x̂) are written.",
            },
        },
    },

    "CMD_OBSERVER_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable a configured observer.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
            },
            "enable": {
                "type": "bool",
                "required": True,
            },
        },
    },

    "CMD_OBSERVER_RESET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Reset observer state estimate to zero.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
            },
        },
    },

    "CMD_OBSERVER_SET_PARAM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set individual matrix element (e.g., 'A01', 'L10').",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
            },
            "key": {
                "type": "string",
                "required": True,
                "description": "Matrix element: 'Aij', 'Bij', 'Cij', or 'Lij' (i=row, j=col).",
            },
            "value": {
                "type": "float",
                "required": True,
            },
        },
    },

    "CMD_OBSERVER_SET_PARAM_ARRAY": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set full matrix (A, B, C, or L) in row-major order.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
            },
            "key": {
                "type": "string",
                "required": True,
                "enum": ["A", "B", "C", "L"],
                "description": "Matrix name.",
            },
            "values": {
                "type": "array",
                "items": {"type": "float"},
                "required": True,
                "description": "Matrix values in row-major order.",
            },
        },
    },

    "CMD_OBSERVER_STATUS": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get observer status and current state estimates.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 3,
            },
        },
    },
}
