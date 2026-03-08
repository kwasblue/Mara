# schema/commands/__init__.py
"""
JSON command definitions for the robot platform.

Commands are organized by domain:
- Safety / State Machine
- Loop Rates
- Control Kernel (Signal Bus, Slots)
- Motion
- GPIO / PWM / LED
- Servo
- Stepper
- DC Motor
- Sensors (Encoder, Ultrasonic)
- Observer
- Telemetry / Logging
- Camera
"""

from ._safety import SAFETY_COMMANDS
from ._rates import RATE_COMMANDS
from ._control import CONTROL_COMMANDS
from ._motion import MOTION_COMMANDS
from ._gpio import GPIO_COMMANDS
from ._servo import SERVO_COMMANDS
from ._stepper import STEPPER_COMMANDS
from ._sensors import SENSOR_COMMANDS
from ._dc_motor import DC_MOTOR_COMMANDS
from ._observer import OBSERVER_COMMANDS
from ._telemetry import TELEMETRY_COMMANDS
from ._camera import CAMERA_COMMANDS

# Merge all command dictionaries
COMMANDS: dict[str, dict] = {
    **SAFETY_COMMANDS,
    **RATE_COMMANDS,
    **CONTROL_COMMANDS,
    **MOTION_COMMANDS,
    **GPIO_COMMANDS,
    **SERVO_COMMANDS,
    **STEPPER_COMMANDS,
    **SENSOR_COMMANDS,
    **DC_MOTOR_COMMANDS,
    **OBSERVER_COMMANDS,
    **TELEMETRY_COMMANDS,
    **CAMERA_COMMANDS,
}

__all__ = [
    "COMMANDS",
    # Individual command groups for selective imports
    "SAFETY_COMMANDS",
    "RATE_COMMANDS",
    "CONTROL_COMMANDS",
    "MOTION_COMMANDS",
    "GPIO_COMMANDS",
    "SERVO_COMMANDS",
    "STEPPER_COMMANDS",
    "SENSOR_COMMANDS",
    "DC_MOTOR_COMMANDS",
    "OBSERVER_COMMANDS",
    "TELEMETRY_COMMANDS",
    "CAMERA_COMMANDS",
]
