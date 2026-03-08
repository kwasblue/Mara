# schema/commands/_control.py
"""Control kernel command definitions (signal bus + slots)."""

CONTROL_COMMANDS: dict[str, dict] = {
    # Signal Bus
    "CMD_CTRL_SIGNAL_DEFINE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Define a new signal in the signal bus. Only allowed when IDLE.",
        "payload": {
            "id": {
                "type": "int",
                "required": True,
                "description": "Unique signal ID.",
            },
            "name": {
                "type": "string",
                "required": True,
                "description": "Human-readable signal name.",
            },
            "signal_kind": {
                "type": "string",
                "required": True,
                "enum": ["REF", "MEAS", "OUT", "EST"],
                "description": "Signal kind: REF = reference/setpoint, MEAS = measurement/feedback, OUT = control output, EST = state estimate.",
            },
            "initial": {
                "type": "float",
                "required": False,
                "default": 0.0,
                "description": "Initial value.",
            },
        },
    },

    "CMD_CTRL_SIGNALS_CLEAR": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Clear all signals from the signal bus.",
        "payload": {},
    },

    "CMD_CTRL_SIGNAL_SET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set a signal value in the signal bus.",
        "payload": {
            "id": {
                "type": "int",
                "required": True,
                "description": "Signal ID.",
            },
            "value": {
                "type": "float",
                "required": True,
                "description": "Value to set.",
            },
        },
    },

    "CMD_CTRL_SIGNAL_GET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get a signal value from the signal bus.",
        "payload": {
            "id": {
                "type": "int",
                "required": True,
                "description": "Signal ID.",
            },
        },
    },

    "CMD_CTRL_SIGNALS_LIST": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "List all defined signals in the signal bus.",
        "payload": {},
    },

    "CMD_CTRL_SIGNAL_DELETE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Delete a signal from the signal bus.",
        "payload": {
            "id": {"type": "integer", "description": "Signal ID to delete"}
        },
    },

    # Slot Configuration
    "CMD_CTRL_SLOT_CONFIG": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Configure a control slot with controller type and signal routing. Only allowed when IDLE.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
            "controller_type": {
                "type": "string",
                "required": True,
                "enum": ["PID", "STATE_SPACE", "SS"],
                "description": "Controller type: PID or STATE_SPACE.",
            },
            "rate_hz": {
                "type": "int",
                "required": False,
                "default": 100,
                "min": 1,
                "max": 1000,
                "description": "Controller update rate in Hz.",
            },
            "ref_id": {
                "type": "int",
                "required": False,
                "description": "Signal ID for reference/setpoint (PID mode).",
            },
            "meas_id": {
                "type": "int",
                "required": False,
                "description": "Signal ID for measurement/feedback (PID mode).",
            },
            "out_id": {
                "type": "int",
                "required": False,
                "description": "Signal ID for control output (PID mode).",
            },
            "num_states": {
                "type": "int",
                "required": False,
                "default": 2,
                "min": 1,
                "max": 6,
                "description": "Number of state variables (STATE_SPACE mode).",
            },
            "num_inputs": {
                "type": "int",
                "required": False,
                "default": 1,
                "min": 1,
                "max": 2,
                "description": "Number of control inputs (STATE_SPACE mode).",
            },
            "state_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": False,
                "description": "Signal IDs for state measurements (STATE_SPACE mode).",
            },
            "ref_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": False,
                "description": "Signal IDs for state references (STATE_SPACE mode).",
            },
            "output_ids": {
                "type": "array",
                "items": {"type": "int"},
                "required": False,
                "description": "Signal IDs for control outputs (STATE_SPACE mode).",
            },
            "require_armed": {
                "type": "bool",
                "required": False,
                "default": True,
                "description": "Only run when robot is armed.",
            },
            "require_active": {
                "type": "bool",
                "required": False,
                "default": True,
                "description": "Only run when robot is active.",
            },
        },
    },

    "CMD_CTRL_SLOT_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable a configured control slot.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
            "enable": {
                "type": "bool",
                "required": True,
                "description": "True to enable, False to disable.",
            },
        },
    },

    "CMD_CTRL_SLOT_GET_PARAM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get a scalar parameter from a control slot's controller.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
            "key": {
                "type": "string",
                "required": True,
                "description": "Parameter name (e.g., 'kp', 'ki', 'kd' for PID; 'k00', 'ki0' for STATE_SPACE).",
            },
        },
    },

    "CMD_CTRL_SLOT_RESET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Reset a control slot's internal state (integrators, etc).",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
        },
    },

    "CMD_CTRL_SLOT_SET_PARAM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set a scalar parameter on a control slot's controller.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
            "key": {
                "type": "string",
                "required": True,
                "description": "Parameter name (e.g., 'kp', 'ki', 'kd', 'out_min', 'out_max' for PID; 'k00', 'ki0', 'u0_min' for STATE_SPACE).",
            },
            "value": {
                "type": "float",
                "required": True,
                "description": "Parameter value.",
            },
        },
    },

    "CMD_CTRL_SLOT_SET_PARAM_ARRAY": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set an array parameter on a control slot (e.g., gain matrix K for state-space).",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
            "key": {
                "type": "string",
                "required": True,
                "description": "Parameter name ('K' = state feedback, 'Kr' = reference feedforward, 'Ki' = integral gains).",
            },
            "values": {
                "type": "array",
                "items": {"type": "float"},
                "required": True,
                "description": "Array of float values. For K/Kr: row-major order [k00,k01,...,k10,k11,...]. For Ki: one per output.",
            },
        },
    },

    "CMD_CTRL_SLOT_STATUS": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get status of a control slot.",
        "payload": {
            "slot": {
                "type": "int",
                "required": True,
                "min": 0,
                "max": 7,
                "description": "Slot index (0-7).",
            },
        },
    },
}
