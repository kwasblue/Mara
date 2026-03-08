# mara_host/__init__.py
"""
Robot Host - Python platform for controlling robots with ESP32 MCU Host firmware.

This library provides a structured platform for building robot control systems.
It handles communication with the MCU firmware while you focus on robot logic.

Quick Start:
    from mara_host import Robot, GPIO, DifferentialDrive

    async def main():
        async with Robot("/dev/ttyUSB0") as robot:
            await robot.arm()

            # Use public API classes
            gpio = GPIO(robot)
            await gpio.register(0, pin=2, mode="output")
            await gpio.high(0)

            drive = DifferentialDrive(robot)
            await drive.drive_straight(1.0, speed=0.3)

    asyncio.run(main())

With Configuration (recommended):
    from mara_host import Robot, RobotConfig

    config = RobotConfig.load("robots/my_robot.yaml")
    errors = config.validate()
    if not errors:
        async with config.create_robot() as robot:
            await robot.arm()

With Runtime (recommended for control loops):
    from mara_host import Robot, Runtime

    async with Robot("/dev/ttyUSB0") as robot:
        runtime = Runtime(robot, tick_hz=50.0)

        @runtime.on_tick
        async def control(dt):
            await robot.motion.set_velocity(0.1, 0.0)

        await runtime.run(duration=10.0)

Public API:
    Core: Robot, Runtime, RobotConfig, BaseModule
    Actuators: Stepper, Servo, DCMotor
    Sensors: Encoder, IMU, Ultrasonic
    I/O: GPIO, PWM
    Control: VelocityController, PIDController, DifferentialDrive

Internal modules (not stable, for advanced use only):
    mara_host.services.* - Service layer (control, camera, telemetry)
    mara_host.motor.* - Motion HostModules
    mara_host.sensor.* - Sensor HostModules
    mara_host.command.* - Command/client internals
    mara_host.core.* - Protocol/event internals
    mara_host.transport.* - Transport layer internals
"""

# Version
__version__ = "0.4.0"

# Core - Main entry points
from .robot import Robot
from .runtime.runtime import Runtime
from .config.robot_config import RobotConfig
from .core.base_module import BaseModule

# Public API - Actuators
from .api.stepper import Stepper
from .api.servo import Servo
from .api.dc_motor import DCMotor

# Public API - Sensors
from .api.encoder import Encoder, EncoderReading
from .api.imu import IMU, IMUReading
from .api.ultrasonic import Ultrasonic, UltrasonicReading

# Public API - I/O
from .api.gpio import GPIO
from .api.pwm import PWM

# Public API - Control
from .api.velocity import VelocityController
from .api.pid_controller import PIDController, PIDGains
from .api.differential_drive import DifferentialDrive, DriveConfig

# Public API
__all__ = [
    # Version
    "__version__",
    # Core
    "Robot",
    "Runtime",
    "RobotConfig",
    "BaseModule",
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
