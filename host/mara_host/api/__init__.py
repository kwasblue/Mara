# mara_host/api/__init__.py
"""
Public API for robot control.

This module is the canonical public interface for mara_host.

## API Layer Architecture

MARA uses a two-layer API structure:

### Primary API (this module)
Hand-written classes with rich features:
- State tracking and caching
- Input validation and bounds checking
- Derived values (e.g., roll/pitch from IMU accelerometer)
- Convenience methods and properties
- Bias correction and calibration

**This is what most users should import.**

### Generated API (mara_host.api.generated)
Minimal schema-driven classes auto-generated from hardware definitions:
- Direct command wrappers with no added logic
- Raw telemetry values without derived calculations
- Useful for debugging or when you need raw access

Example:
    # Primary API (recommended)
    from mara_host.api import IMU
    imu = IMU(robot)
    print(imu.roll_deg)  # Derived orientation

    # Raw API (same module, explicit naming)
    from mara_host.api import ImuRaw
    imu = ImuRaw(robot)
    print(imu.reading.ax_mg)  # Raw milli-g value

    # Or import from generated submodule directly
    from mara_host.api.generated import Imu
    imu = Imu(robot)
    print(imu.reading.ax_mg)  # Raw milli-g value

## Available Classes

Actuators:
    Stepper - Stepper motor control with acceleration profiles
    Servo - Servo motor control with angle/pulse conversion
    DCMotor - DC motor with PWM speed control and direction

Sensors:
    Encoder - Quadrature encoder with position/velocity tracking
    IMU - Inertial measurement unit with bias correction and orientation
    Ultrasonic - Ultrasonic distance sensor with averaging
    TelemetrySensor - Base class for custom telemetry sensors

I/O:
    GPIO - Digital I/O with channel registration
    PWM - PWM output control

Control:
    VelocityController - High-rate velocity streaming
    PIDController - Velocity PID for DC motors
    DifferentialDrive - Motion primitives for diff drive robots
    SignalBus - Signal bus for control systems
    ObserverSlotManager - Observer slot management

Note: For state-space controllers, use mara_host.control.upload:
    from mara_host.control.upload import ControllerConfig, upload_controller

Note: For PID via control graphs, use mara_host.tools.schema.control_graph.builders:
    from mara_host.tools.schema.control_graph.builders import PIDConfig, build_pid_graph

Utilities:
    Recording - Session recording and replay
    Testing - Hardware testing framework
    Pins - Pin management and validation
"""

# =============================================================================
# Primary API - Rich hand-written classes (recommended for most users)
# =============================================================================
from .stepper import Stepper
from .servo import Servo
from .dc_motor import DCMotor
from .encoder import Encoder, EncoderReading
from .imu import IMU, IMUReading
from .ultrasonic import Ultrasonic, UltrasonicReading
from .sensor_base import TelemetrySensor
from .velocity import VelocityController
from .gpio import GPIO
from .pwm import PWM
from .pid_controller import PIDController, PIDGains
from .differential_drive import DifferentialDrive, DriveConfig
from .signals import SignalBus, Signal, SignalKind
from .observer_slot import ObserverSlotManager, ObserverSlot, ObserverConfig
from .recording import Recording, RecordingSession, RecordingEvent
from .testing import Testing, TestResult, TestSuite, TestStatus
from .pins import Pins, PinInfo, PinFunction, PinConflict

# =============================================================================
# Raw API - Minimal generated classes (for debugging/low-level access)
# =============================================================================
# These are aliases to make the relationship explicit at the import level.
# Use these when you need raw telemetry values without derived calculations.
from .generated.imu import Imu as ImuRaw, ImuReading as ImuRawReading
from .generated.encoder import Encoder as EncoderRaw, EncoderReading as EncoderRawReading
from .generated.ultrasonic import Ultrasonic as UltrasonicRaw, UltrasonicReading as UltrasonicRawReading
from .generated.servo import Servo as ServoRaw, ServoState as ServoRawState
from .generated.dc_motor import DcMotor as DcMotorRaw, DcMotorState as DcMotorRawState
from .generated.stepper import Stepper as StepperRaw, StepperState as StepperRawState
from .generated.lidar import Lidar as LidarRaw, LidarReading as LidarRawReading
from .generated.ir import IrSensor as IrSensorRaw, IrReading as IrRawReading
from .generated.temp import Temperature as TemperatureRaw, TemperatureReading as TemperatureRawReading

__all__ = [
    # ==========================================================================
    # Primary API - Rich hand-written classes
    # ==========================================================================
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
    "TelemetrySensor",
    # I/O
    "GPIO",
    "PWM",
    # Control
    "VelocityController",
    "PIDController",
    "PIDGains",
    "DifferentialDrive",
    "DriveConfig",
    # Signal Bus & Slots
    "SignalBus",
    "Signal",
    "SignalKind",
    "ObserverSlotManager",
    "ObserverSlot",
    "ObserverConfig",
    # Utilities
    "Recording",
    "RecordingSession",
    "RecordingEvent",
    "Testing",
    "TestResult",
    "TestSuite",
    "TestStatus",
    "Pins",
    "PinInfo",
    "PinFunction",
    "PinConflict",
    # ==========================================================================
    # Raw API - Minimal generated classes (for debugging/low-level access)
    # ==========================================================================
    "ImuRaw",
    "ImuRawReading",
    "EncoderRaw",
    "EncoderRawReading",
    "UltrasonicRaw",
    "UltrasonicRawReading",
    "ServoRaw",
    "ServoRawState",
    "DcMotorRaw",
    "DcMotorRawState",
    "StepperRaw",
    "StepperRawState",
    "LidarRaw",
    "LidarRawReading",
    "IrSensorRaw",
    "IrRawReading",
    "TemperatureRaw",
    "TemperatureRawReading",
]
