# robot_host/__init__.py
"""
Robot Host - Python platform for controlling robots with ESP32 MCU Host firmware.

This library provides a structured platform for building robot control systems.
It handles communication with the MCU firmware while you focus on robot logic.

Quick Start:
    from robot_host import Robot, GPIO, DifferentialDrive

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

With Configuration:
    from robot_host import Robot
    from robot_host.config import RobotConfig

    config = RobotConfig.load("robots/my_robot.yaml")
    errors = config.validate()
    if not errors:
        async with config.create_robot() as robot:
            await robot.arm()

With Runtime:
    from robot_host import Robot
    from robot_host.runtime import Runtime

    async with Robot("/dev/ttyUSB0") as robot:
        runtime = Runtime(robot, tick_hz=50.0)

        @runtime.on_tick
        async def control(dt):
            await robot.motion.set_velocity(0.1, 0.0)

        await runtime.run(duration=10.0)

Public API (robot_host.api):
    Actuators: Stepper, Servo, DCMotor
    Sensors: Encoder, IMU, Ultrasonic
    I/O: GPIO, PWM
    Control: VelocityController, PIDController, DifferentialDrive

Configuration (robot_host.config):
    RobotConfig - First-class configuration object

Runtime (robot_host.runtime):
    Runtime - Canonical runtime loop

Internal modules (for advanced use):
    robot_host.hw.* - Hardware HostModules
    robot_host.motor.* - Motor HostModules
    robot_host.sensor.* - Sensor HostModules
    robot_host.command.client - AsyncRobotClient
    robot_host.core.event_bus - EventBus
"""

# Version
__version__ = "0.4.0"

# Main entry point
from .robot import Robot

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
    # Main
    "Robot",
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
