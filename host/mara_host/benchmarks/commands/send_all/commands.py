# mara_host/benchmarks/commands/send_all/commands.py
"""Command constants and categorization."""
from __future__ import annotations

from typing import Dict, List, Set


# =============================================================================
# Command Constants
# =============================================================================

# Safety / State Machine
CMD_HEARTBEAT = "CMD_HEARTBEAT"
CMD_ARM = "CMD_ARM"
CMD_DISARM = "CMD_DISARM"
CMD_ACTIVATE = "CMD_ACTIVATE"
CMD_DEACTIVATE = "CMD_DEACTIVATE"
CMD_ESTOP = "CMD_ESTOP"
CMD_CLEAR_ESTOP = "CMD_CLEAR_ESTOP"
CMD_STOP = "CMD_STOP"

# Loop Rates
CMD_GET_RATES = "CMD_GET_RATES"
CMD_CTRL_SET_RATE = "CMD_CTRL_SET_RATE"
CMD_SAFETY_SET_RATE = "CMD_SAFETY_SET_RATE"
CMD_TELEM_SET_RATE = "CMD_TELEM_SET_RATE"

# Control Kernel - Slots
CMD_CTRL_SLOT_CONFIG = "CMD_CTRL_SLOT_CONFIG"
CMD_CTRL_SLOT_ENABLE = "CMD_CTRL_SLOT_ENABLE"
CMD_CTRL_SLOT_RESET = "CMD_CTRL_SLOT_RESET"
CMD_CTRL_SLOT_SET_PARAM = "CMD_CTRL_SLOT_SET_PARAM"
CMD_CTRL_SLOT_STATUS = "CMD_CTRL_SLOT_STATUS"

# Control Kernel - Signals
CMD_CTRL_SIGNAL_DEFINE = "CMD_CTRL_SIGNAL_DEFINE"
CMD_CTRL_SIGNAL_SET = "CMD_CTRL_SIGNAL_SET"
CMD_CTRL_SIGNAL_GET = "CMD_CTRL_SIGNAL_GET"
CMD_CTRL_SIGNALS_LIST = "CMD_CTRL_SIGNALS_LIST"

# Legacy / Mode
CMD_SET_MODE = "CMD_SET_MODE"

# Motion
CMD_SET_VEL = "CMD_SET_VEL"

# LED
CMD_LED_ON = "CMD_LED_ON"
CMD_LED_OFF = "CMD_LED_OFF"

# GPIO
CMD_GPIO_WRITE = "CMD_GPIO_WRITE"
CMD_GPIO_READ = "CMD_GPIO_READ"
CMD_GPIO_TOGGLE = "CMD_GPIO_TOGGLE"
CMD_GPIO_REGISTER_CHANNEL = "CMD_GPIO_REGISTER_CHANNEL"

# PWM
CMD_PWM_SET = "CMD_PWM_SET"

# Servo
CMD_SERVO_ATTACH = "CMD_SERVO_ATTACH"
CMD_SERVO_DETACH = "CMD_SERVO_DETACH"
CMD_SERVO_SET_ANGLE = "CMD_SERVO_SET_ANGLE"

# Stepper
CMD_STEPPER_ENABLE = "CMD_STEPPER_ENABLE"
CMD_STEPPER_MOVE_REL = "CMD_STEPPER_MOVE_REL"
CMD_STEPPER_STOP = "CMD_STEPPER_STOP"

# Ultrasonic
CMD_ULTRASONIC_ATTACH = "CMD_ULTRASONIC_ATTACH"
CMD_ULTRASONIC_READ = "CMD_ULTRASONIC_READ"

# Telemetry
CMD_TELEM_SET_INTERVAL = "CMD_TELEM_SET_INTERVAL"

# Logging
CMD_SET_LOG_LEVEL = "CMD_SET_LOG_LEVEL"

# Encoders
CMD_ENCODER_ATTACH = "CMD_ENCODER_ATTACH"
CMD_ENCODER_READ = "CMD_ENCODER_READ"
CMD_ENCODER_RESET = "CMD_ENCODER_RESET"

# DC Motor
CMD_DC_SET_SPEED = "CMD_DC_SET_SPEED"
CMD_DC_STOP = "CMD_DC_STOP"
CMD_DC_VEL_PID_ENABLE = "CMD_DC_VEL_PID_ENABLE"
CMD_DC_SET_VEL_TARGET = "CMD_DC_SET_VEL_TARGET"
CMD_DC_SET_VEL_GAINS = "CMD_DC_SET_VEL_GAINS"


# =============================================================================
# Command Lists
# =============================================================================

ALL_COMMANDS: List[str] = [
    # Safety / State Machine
    CMD_HEARTBEAT,
    CMD_ARM,
    CMD_DISARM,
    CMD_ACTIVATE,
    CMD_DEACTIVATE,
    CMD_ESTOP,
    CMD_CLEAR_ESTOP,
    CMD_STOP,

    # Loop Rates
    CMD_GET_RATES,
    CMD_CTRL_SET_RATE,
    CMD_SAFETY_SET_RATE,
    CMD_TELEM_SET_RATE,

    # Control Kernel - Signals
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SIGNAL_SET,
    CMD_CTRL_SIGNAL_GET,
    CMD_CTRL_SIGNALS_LIST,

    # Control Kernel - Slots
    CMD_CTRL_SLOT_CONFIG,
    CMD_CTRL_SLOT_ENABLE,
    CMD_CTRL_SLOT_RESET,
    CMD_CTRL_SLOT_SET_PARAM,
    CMD_CTRL_SLOT_STATUS,

    # Legacy / Mode
    CMD_SET_MODE,

    # Motion
    CMD_SET_VEL,

    # LED
    CMD_LED_ON,
    CMD_LED_OFF,

    # GPIO
    CMD_GPIO_WRITE,
    CMD_GPIO_READ,
    CMD_GPIO_TOGGLE,
    CMD_GPIO_REGISTER_CHANNEL,

    # PWM
    CMD_PWM_SET,

    # Servo
    CMD_SERVO_ATTACH,
    CMD_SERVO_DETACH,
    CMD_SERVO_SET_ANGLE,

    # Stepper
    CMD_STEPPER_ENABLE,
    CMD_STEPPER_MOVE_REL,
    CMD_STEPPER_STOP,

    # Ultrasonic
    CMD_ULTRASONIC_ATTACH,
    CMD_ULTRASONIC_READ,

    # Telemetry
    CMD_TELEM_SET_INTERVAL,

    # Logging
    CMD_SET_LOG_LEVEL,

    # Encoders
    CMD_ENCODER_ATTACH,
    CMD_ENCODER_READ,
    CMD_ENCODER_RESET,

    # DC Motor
    CMD_DC_SET_SPEED,
    CMD_DC_STOP,
    CMD_DC_VEL_PID_ENABLE,
    CMD_DC_SET_VEL_TARGET,
    CMD_DC_SET_VEL_GAINS,
]


# =============================================================================
# Command Sets
# =============================================================================

MOTION_COMMANDS: Set[str] = {
    CMD_ACTIVATE,
    CMD_SET_VEL,
    CMD_DC_SET_SPEED,
    CMD_DC_SET_VEL_TARGET,
    CMD_SERVO_SET_ANGLE,
    CMD_STEPPER_MOVE_REL,
    CMD_STEPPER_ENABLE,
    CMD_CTRL_SLOT_ENABLE,
}

DISRUPTIVE_COMMANDS: Set[str] = {CMD_ESTOP}

REQUIRES_PAYLOAD: Set[str] = {
    CMD_GPIO_REGISTER_CHANNEL, CMD_GPIO_READ, CMD_GPIO_WRITE, CMD_GPIO_TOGGLE,
    CMD_SET_MODE,
    CMD_SET_VEL,
    CMD_PWM_SET,
    CMD_SERVO_ATTACH, CMD_SERVO_DETACH, CMD_SERVO_SET_ANGLE,
    CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP,
    CMD_ULTRASONIC_ATTACH, CMD_ULTRASONIC_READ,
    CMD_ENCODER_ATTACH, CMD_ENCODER_READ, CMD_ENCODER_RESET,
    CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_DC_VEL_PID_ENABLE, CMD_DC_SET_VEL_TARGET, CMD_DC_SET_VEL_GAINS,
    CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE,
    CMD_CTRL_SLOT_CONFIG, CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET, CMD_CTRL_SLOT_SET_PARAM, CMD_CTRL_SLOT_STATUS,
    CMD_CTRL_SIGNAL_DEFINE, CMD_CTRL_SIGNAL_SET, CMD_CTRL_SIGNAL_GET,
    CMD_TELEM_SET_INTERVAL,
    CMD_SET_LOG_LEVEL,
}

REQUIRES_IDLE: Set[str] = {
    CMD_CTRL_SET_RATE,
    CMD_SAFETY_SET_RATE,
    CMD_TELEM_SET_RATE,
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SLOT_CONFIG,
}

NO_PAYLOAD_OK: Set[str] = {
    CMD_HEARTBEAT,
    CMD_ARM,
    CMD_DISARM,
    CMD_ACTIVATE,
    CMD_DEACTIVATE,
    CMD_ESTOP,
    CMD_CLEAR_ESTOP,
    CMD_STOP,
    CMD_LED_ON,
    CMD_LED_OFF,
    CMD_GET_RATES,
    CMD_CTRL_SIGNALS_LIST,
}

IDLE_ONLY_COMMANDS: Set[str] = set(REQUIRES_IDLE)

SOFT_SKIP_ERRORS: Set[str] = {"no_control_module", "not_supported"}

NO_ACK_LIKE_ERRORS: Set[str] = {"CLEARED", "CANCELLED"}

CONTROL_COMMANDS: Set[str] = {
    CMD_CTRL_SLOT_CONFIG,
    CMD_CTRL_SLOT_ENABLE,
    CMD_CTRL_SLOT_RESET,
    CMD_CTRL_SLOT_SET_PARAM,
    CMD_CTRL_SLOT_STATUS,
    CMD_CTRL_SIGNAL_DEFINE,
    CMD_CTRL_SIGNAL_SET,
    CMD_CTRL_SIGNAL_GET,
    CMD_CTRL_SIGNALS_LIST,
}


# =============================================================================
# Category Helpers
# =============================================================================

def get_command_category(cmd: str) -> str:
    """Get the category for a command."""
    categories: Dict[str, Set[str]] = {
        "safety": {CMD_HEARTBEAT, CMD_ARM, CMD_DISARM, CMD_ACTIVATE, CMD_DEACTIVATE, CMD_ESTOP, CMD_CLEAR_ESTOP, CMD_STOP, CMD_SET_MODE},
        "rates": {CMD_GET_RATES, CMD_CTRL_SET_RATE, CMD_SAFETY_SET_RATE, CMD_TELEM_SET_RATE},
        "control": {CMD_CTRL_SLOT_CONFIG, CMD_CTRL_SLOT_ENABLE, CMD_CTRL_SLOT_RESET, CMD_CTRL_SLOT_SET_PARAM, CMD_CTRL_SLOT_STATUS,
                    CMD_CTRL_SIGNAL_DEFINE, CMD_CTRL_SIGNAL_SET, CMD_CTRL_SIGNAL_GET, CMD_CTRL_SIGNALS_LIST},
        "gpio": {CMD_GPIO_WRITE, CMD_GPIO_READ, CMD_GPIO_TOGGLE, CMD_GPIO_REGISTER_CHANNEL},
        "led": {CMD_LED_ON, CMD_LED_OFF},
        "pwm": {CMD_PWM_SET},
        "servo": {CMD_SERVO_ATTACH, CMD_SERVO_DETACH, CMD_SERVO_SET_ANGLE},
        "stepper": {CMD_STEPPER_ENABLE, CMD_STEPPER_MOVE_REL, CMD_STEPPER_STOP},
        "ultrasonic": {CMD_ULTRASONIC_ATTACH, CMD_ULTRASONIC_READ},
        "encoder": {CMD_ENCODER_ATTACH, CMD_ENCODER_READ, CMD_ENCODER_RESET},
        "dc": {CMD_DC_SET_SPEED, CMD_DC_STOP, CMD_DC_VEL_PID_ENABLE, CMD_DC_SET_VEL_TARGET, CMD_DC_SET_VEL_GAINS},
        "motion": {CMD_SET_VEL},
        "telem": {CMD_TELEM_SET_INTERVAL},
        "logging": {CMD_SET_LOG_LEVEL},
    }
    for cat, cmds in categories.items():
        if cmd in cmds:
            return cat
    return "other"


def filter_commands(cmds: List[str], only: str | None, skip: str | None, category: str | None = None) -> List[str]:
    """Filter commands based on only/skip lists and category."""
    only_set = set([c.strip() for c in only.split(",") if c.strip()]) if only else None
    skip_set = set([c.strip() for c in skip.split(",") if c.strip()]) if skip else set()

    out: List[str] = []
    for c in cmds:
        if only_set is not None and c not in only_set:
            continue
        if c in skip_set:
            continue
        if category and get_command_category(c) != category:
            continue
        out.append(c)
    return out
