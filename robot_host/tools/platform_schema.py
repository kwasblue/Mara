# platform_schema.py
"""
Single source of truth for the robot platform:

- PINS: numeric mapping (from pins.json)
- COMMANDS: JSON command schema
- GPIO_CHANNELS: logical GPIO channel mapping
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

# Location of pins.json (same as in your current gen_pins.py)
PINS_JSON = Path("/Users/kwasiaddo/projects/Host/robot_host/config/pins.json")


# === 1) PINS: loaded from pins.json ===

def _load_pins(path: Path) -> dict:
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


PINS: dict[str, int] = _load_pins(PINS_JSON)

# === 2) VERSION INFO ===
VERSION: dict[str, any] = {
    "firmware": "1.0.0",
    "protocol": 1,
    "schema_version": 1,  # Schema evolution version
    "board": "esp32",
    "name": "robot",
}

# === 2b) CAPABILITIES ===
# Bitfield for feature advertisement (matches MCU Version.h)
CAPABILITIES = {
    "BINARY_PROTOCOL": 0x0001,   # Binary frame protocol support
    "INTENT_BUFFERING": 0x0002, # Command-to-actuator intent buffering
    "STATE_SPACE_CTRL": 0x0004, # State-space controller support
    "OBSERVERS": 0x0008,        # Luenberger observer support
}

# Combined capability mask (must match MCU)
CAPABILITIES_MASK = (
    CAPABILITIES["BINARY_PROTOCOL"] |
    CAPABILITIES["INTENT_BUFFERING"] |
    CAPABILITIES["STATE_SPACE_CTRL"] |
    CAPABILITIES["OBSERVERS"]
)
# === 3) COMMANDS: your existing schema, unchanged in spirit ===

COMMANDS: dict[str, dict] = {
    # ----------------------------------------------------------------------
    # Safety / State Machine
    # ----------------------------------------------------------------------
    "CMD_HEARTBEAT": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Host heartbeat to maintain connection. Resets host timeout watchdog.",
        "payload": {},
    },

    "CMD_ARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from IDLE to ARMED. Motors enabled but not accepting motion.",
        "payload": {},
    },

    "CMD_DISARM": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to IDLE. Motors disabled.",
        "payload": {},
    },

    "CMD_ACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ARMED to ACTIVE. Motion commands now accepted.",
        "payload": {},
    },

    "CMD_DEACTIVATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Transition from ACTIVE to ARMED. Stops motion, still armed.",
        "payload": {},
    },

    "CMD_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Emergency stop, immediately disable motion.",
        "payload": {},
    },

    "CMD_CLEAR_ESTOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Clear ESTOP and return to IDLE mode.",
        "payload": {},
    },

    "CMD_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Stop all motion (soft stop).",
        "payload": {},
    },

    # ----------------------------------------------------------------------
    # Loop Rates
    # ----------------------------------------------------------------------
    "CMD_GET_RATES": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get current loop rates (ctrl, safety, telem) in Hz.",
        "payload": {},
    },

    "CMD_CTRL_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set control loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 5,
                "max": 200,
                "description": "Control loop frequency in Hz.",
            },
        },
    },

    "CMD_SAFETY_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set safety loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 20,
                "max": 500,
                "description": "Safety loop frequency in Hz.",
            },
        },
    },

    "CMD_TELEM_SET_RATE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set telemetry loop rate in Hz. Only allowed when IDLE.",
        "payload": {
            "hz": {
                "type": "int",
                "required": True,
                "min": 1,
                "max": 50,
                "description": "Telemetry loop frequency in Hz.",
            },
        },
    },

    # ----------------------------------------------------------------------
    # Control Kernel - Signal Bus
    # ----------------------------------------------------------------------
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
    # ----------------------------------------------------------------------
    # Control Kernel - Slot Configuration
    # ----------------------------------------------------------------------
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
            # PID signals (used when controller_type = "PID")
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
            # State-space signals (used when controller_type = "STATE_SPACE" or "SS")
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

    # ----------------------------------------------------------------------
    # Robot Core
    # ----------------------------------------------------------------------
    "CMD_SET_MODE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set the high-level robot mode. Prefer ARM/ACTIVATE/DISARM/DEACTIVATE.",
        "payload": {
            "mode": {
                "type": "string",
                "required": True,
                "enum": ["IDLE", "ARMED", "ACTIVE", "CALIB"],
            }
        },
    },

    "CMD_SET_VEL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set linear and angular velocity in robot frame.",
        "payload": {
            "vx": {"type": "float", "required": True, "units": "m/s"},
            "omega": {"type": "float", "required": True, "units": "rad/s"},
            "frame": {
                "type": "string",
                "required": False,
                "default": "robot",
                "enum": ["robot", "world"],
            },
        },
    },

    # ----------------------------------------------------------------------
    # LED
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # GPIO
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # PWM
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # Servo
    # ----------------------------------------------------------------------
    "CMD_SERVO_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach a servo ID to a physical pin.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
            "channel": {"type": "int", "required": True},
            "min_us": {"type": "int", "required": False, "default": 1000},
            "max_us": {"type": "int", "required": False, "default": 2000},
        },
    },

    "CMD_SERVO_DETACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Detach a servo ID.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
        },
    },

    "CMD_SERVO_SET_ANGLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set servo angle in degrees.",
        "payload": {
            "servo_id": {"type": "int", "required": True},
            "angle_deg": {"type": "float", "required": True},
            "duration_ms": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Interpolation duration in milliseconds (0 = immediate).",
            },
        },
    },

    # ----------------------------------------------------------------------
    # Stepper
    # ----------------------------------------------------------------------
    "CMD_STEPPER_MOVE_REL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Move a stepper a relative number of steps.",
        "payload": {
            "motor_id": {"type": "int", "required": True},
            "steps": {"type": "int", "required": True},
            "speed_steps_s": {
                "type": "float",
                "required": False,
                "default": 1000.0,
            },
        },
    },

    "CMD_STEPPER_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Immediately stop a stepper motor.",
        "payload": {
            "motor_id": {"type": "int", "required": True},
        },
    },

    "CMD_STEPPER_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable a stepper driver (via enable pin).",
        "payload": {
            "motor_id": {"type": "int", "required": True},
            "enable": {
                "type": "bool",
                "required": False,
                "default": True,
            },
        },
    },

    # ----------------------------------------------------------------------
    # Ultrasonic
    # ----------------------------------------------------------------------
    "CMD_ULTRASONIC_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach/configure an ultrasonic sensor for the given logical sensor_id.",
        "payload": {
            "sensor_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    "CMD_ULTRASONIC_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Trigger a single ultrasonic distance measurement.",
        "payload": {
            "sensor_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    # ----------------------------------------------------------------------
    # Telemetry
    # ----------------------------------------------------------------------
    "CMD_TELEM_SET_INTERVAL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set telemetry publish interval in milliseconds (0 = disable).",
        "payload": {
            "interval_ms": {
                "type": "int",
                "required": True,
                "default": 100,
            },
        },
    },

    # ----------------------------------------------------------------------
    # Logging
    # ----------------------------------------------------------------------
    "CMD_SET_LOG_LEVEL": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set MCU logging verbosity level.",
        "payload": {
            "level": {
                "type": "string",
                "required": True,
                "enum": ["debug", "info", "warn", "error", "off"],
                "default": "info",
            },
        },
    },

    # ----------------------------------------------------------------------
    # Encoders
    # ----------------------------------------------------------------------
    "CMD_ENCODER_ATTACH": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Attach/configure a quadrature encoder with runtime pins.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
            "pin_a": {
                "type": "int",
                "required": True,
                "default": 32,
            },
            "pin_b": {
                "type": "int",
                "required": True,
                "default": 33,
            },
        },
    },

    "CMD_ENCODER_READ": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Request current tick count for a given encoder.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    "CMD_ENCODER_RESET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Reset the tick count for a given encoder back to zero.",
        "payload": {
            "encoder_id": {
                "type": "int",
                "required": True,
                "default": 0,
            },
        },
    },

    # ----------------------------------------------------------------------
    # DC Motor
    # ----------------------------------------------------------------------
    "CMD_DC_SET_SPEED": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set DC motor speed and direction for a given motor ID.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "speed": {
                "type": "float",
                "required": True,
                "description": "Normalized speed in [-1.0, 1.0]; sign = direction.",
                "min": -1.0,
                "max": 1.0,
            },
        },
    },

    "CMD_DC_STOP": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Stop a DC motor (set speed to zero).",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
        },
    },
    # ----------------------------------------------------------------------
    # Observer Commands
    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    # DC Motor – Velocity PID
    # ----------------------------------------------------------------------
    "CMD_DC_VEL_PID_ENABLE": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Enable or disable closed-loop velocity PID control for a DC motor.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "enable": {
                "type": "bool",
                "required": True,
                "description": "True to enable velocity PID, False to disable.",
            },
        },
    },

    "CMD_DC_SET_VEL_TARGET": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Set desired angular velocity target for a DC motor's PID controller.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "omega": {
                "type": "float",
                "required": True,
                "description": "Target angular velocity in rad/s (sign indicates direction).",
            },
        },
    },

    "CMD_DC_SET_VEL_GAINS": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Configure PID gains for DC motor velocity control.",
        "payload": {
            "motor_id": {
                "type": "int",
                "required": True,
                "description": "Logical DC motor ID (0..3).",
            },
            "kp": {
                "type": "float",
                "required": True,
                "description": "Proportional gain for velocity PID.",
            },
            "ki": {
                "type": "float",
                "required": True,
                "description": "Integral gain for velocity PID.",
            },
            "kd": {
                "type": "float",
                "required": True,
                "description": "Derivative gain for velocity PID.",
            },
        },
    },
}


# === 4) TELEMETRY SECTIONS: Binary telemetry section IDs ===
#
# Section IDs for binary telemetry packets.
# Must match MCU registerBinProvider(section_id, ...) calls.

TELEMETRY_SECTIONS: dict[str, dict] = {
    "TELEM_IMU": {
        "id": 0x01,
        "description": "IMU sensor data (accel, gyro, temp)",
        "format": "online(u8) ok(u8) ax(i16) ay(i16) az(i16) gx(i16) gy(i16) gz(i16) temp(i16)",
        "size": 18,
    },
    "TELEM_ULTRASONIC": {
        "id": 0x02,
        "description": "Ultrasonic distance sensor",
        "format": "sensor_id(u8) attached(u8) ok(u8) dist_mm(u16)",
        "size": 5,
    },
    "TELEM_LIDAR": {
        "id": 0x03,
        "description": "LiDAR distance sensor",
        "format": "online(u8) ok(u8) dist_mm(u16) signal(u16)",
        "size": 6,
    },
    "TELEM_ENCODER0": {
        "id": 0x04,
        "description": "Encoder 0 tick count",
        "format": "ticks(i32)",
        "size": 4,
    },
    "TELEM_STEPPER0": {
        "id": 0x05,
        "description": "Stepper motor 0 state",
        "format": "motor_id(i8) attached(u8) enabled(u8) moving(u8) dir(u8) steps(i32) speed(i16)",
        "size": 11,
    },
    "TELEM_DC_MOTOR0": {
        "id": 0x06,
        "description": "DC motor 0 state",
        "format": "attached(u8) speed_centi(i16)",
        "size": 3,
    },
    "TELEM_CTRL_SIGNALS": {
        "id": 0x10,
        "description": "Control signal bus values",
        "format": "count(u16) [id(u16) value(f32) ts_ms(u32)]*",
        "size": None,  # Variable length
    },
    "TELEM_CTRL_OBSERVERS": {
        "id": 0x11,
        "description": "Observer state estimates",
        "format": "slot_count(u8) [slot(u8) enabled(u8) num_states(u8) states(f32)*]*",
        "size": None,  # Variable length
    },
    "TELEM_CTRL_SLOTS": {
        "id": 0x12,
        "description": "Control slot status",
        "format": "slot_count(u8) [slot(u8) enabled(u8) ok(u8) run_count(u32)]*",
        "size": None,  # Variable length
    },
}


# === 5) BINARY COMMANDS: High-rate streaming commands ===
#
# Binary commands are compact fixed-format messages for control loops.
# Use JSON commands for setup/config, binary for real-time streaming (50+ Hz).

BINARY_COMMANDS: dict[str, dict] = {
    "SET_VEL": {
        "opcode": 0x10,
        "json_cmd": "CMD_SET_VEL",  # Maps to JSON equivalent
        "description": "Set velocity: vx(f32), omega(f32)",
        "payload": [
            {"name": "vx", "type": "f32"},
            {"name": "omega", "type": "f32"},
        ],
    },
    "SET_SIGNAL": {
        "opcode": 0x11,
        "json_cmd": "CMD_CTRL_SIGNAL_SET",
        "description": "Set signal: id(u16), value(f32)",
        "payload": [
            {"name": "id", "type": "u16"},
            {"name": "value", "type": "f32"},
        ],
    },
    "SET_SIGNALS": {
        "opcode": 0x12,
        "json_cmd": None,  # Batch-only, no JSON equivalent
        "description": "Set multiple signals: count(u8), [id(u16), value(f32)]*",
        "payload": [
            {"name": "count", "type": "u8"},
        ],
        "variable_length": True,  # [id:u16, value:f32] * count follows
        "variable_item": [
            {"name": "id", "type": "u16"},
            {"name": "value", "type": "f32"},
        ],
    },
    "HEARTBEAT": {
        "opcode": 0x20,
        "json_cmd": "CMD_HEARTBEAT",
        "description": "Heartbeat (no payload)",
        "payload": [],
    },
    "STOP": {
        "opcode": 0x21,
        "json_cmd": "CMD_STOP",
        "description": "Stop (no payload)",
        "payload": [],
    },
}


# === 6) GPIO logical channels ===
#
# pin_name must be a key in PINS.

GPIO_CHANNELS: list[dict] = [
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


def validate_schema() -> None:
    # 1) validate GPIO_CHANNELS pin_name exists in PINS
    seen_channels = set()
    seen_names = set()

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

    # you can also optionally run your COMMANDS validation here if you want


# Run basic validation at import time (optional but nice)
validate_schema()
