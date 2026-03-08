# mara_host/api/__init__.py
"""
Public API for robot control.

This is the canonical public interface for mara_host. These classes wrap
the internal Services layer (services/control/) and provide:
- State tracking
- Input validation
- Convenience methods
- Clear documentation

Actuators:
    Stepper - Stepper motor control
    Servo - Servo motor control
    DCMotor - DC motor with PWM speed control

Sensors:
    Encoder - Quadrature encoder
    IMU - Inertial measurement unit
    Ultrasonic - Ultrasonic distance sensor

I/O:
    GPIO - Digital I/O with channel registration
    PWM - PWM output control

Control:
    VelocityController - High-rate velocity streaming
    PIDController - Velocity PID for DC motors
    DifferentialDrive - Motion primitives for diff drive robots
"""

from .stepper import Stepper
from .servo import Servo
from .dc_motor import DCMotor
from .encoder import Encoder, EncoderReading
from .imu import IMU, IMUReading
from .ultrasonic import Ultrasonic, UltrasonicReading
from .velocity import VelocityController
from .gpio import GPIO
from .pwm import PWM
from .pid_controller import PIDController, PIDGains
from .differential_drive import DifferentialDrive, DriveConfig

__all__ = [
    # Actuators
    "Stepper",
    "Servo",
    "DCMotor",
    # Sensors
    "Encoder",
    "EncoderReading",
    "IMU",
    "IMUReading",
    "Ultrasonic",
    "UltrasonicReading",
    # I/O
    "GPIO",
    "PWM",
    # Control
    "VelocityController",
    "PIDController",
    "PIDGains",
    "DifferentialDrive",
    "DriveConfig",
]
