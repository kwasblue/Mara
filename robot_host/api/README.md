# Robot Host Public API

This directory contains the **public interface** for robot_host.

## Architecture

```
Public (this layer)          Internal (for advanced use)
─────────────────────        ─────────────────────────────
api/GPIO                  →  hw/GpioHostModule
api/PWM                   →  hw/PwmHostModule
api/DifferentialDrive     →  motor/MotionHostModule
api/PIDController         →  (client commands)
api/Encoder               →  sensor/EncoderHostModule
...
```

## Usage

All API classes take a `Robot` instance as their first argument:

```python
from robot_host import Robot, GPIO, DifferentialDrive, PIDController

async with Robot("/dev/ttyUSB0") as robot:
    # I/O
    gpio = GPIO(robot)
    await gpio.register(0, pin=2, mode="output")
    await gpio.high(0)

    # Motion
    drive = DifferentialDrive(robot, wheel_radius=0.05, wheel_base=0.2)
    await drive.drive_straight(1.0, speed=0.3)
    await drive.turn(90)

    # Control
    pid = PIDController(robot, motor_id=0)
    await pid.set_gains(kp=1.0, ki=0.1, kd=0.01)
    await pid.enable()
    await pid.set_target(10.0)  # rad/s
```

## Classes

### Actuators

| Class | Description |
|-------|-------------|
| `Stepper` | Stepper motor control |
| `Servo` | Servo motor control |
| `DCMotor` | DC motor with PWM speed control |

### Sensors

| Class | Description |
|-------|-------------|
| `Encoder` | Quadrature encoder with callbacks |
| `IMU` | Inertial measurement unit |
| `Ultrasonic` | Ultrasonic distance sensor |

### I/O

| Class | Description |
|-------|-------------|
| `GPIO` | Digital I/O with channel registration |
| `PWM` | PWM output control with state tracking |

### Control

| Class | Description |
|-------|-------------|
| `VelocityController` | High-rate velocity streaming |
| `PIDController` | Velocity PID for DC motors |
| `DifferentialDrive` | Motion primitives (drive_straight, turn, arc) |

## BaseModule Interface

For building custom runtime modules, extend `BaseModule`:

```python
from robot_host import Robot, BaseModule
from robot_host.runtime import Runtime

class OdometryModule(BaseModule):
    name = "odometry"

    def topics(self):
        return ["telemetry.encoder0"]

    def on_telemetry_encoder0(self, data):
        self.x += data["delta_x"]
        self.y += data["delta_y"]

    async def on_tick(self, dt: float):
        # Called every tick by Runtime
        pass

async with Robot("/dev/ttyUSB0") as robot:
    runtime = Runtime(robot, tick_hz=50.0)
    runtime.add_module(OdometryModule())
    await runtime.run(duration=10.0)
```

BaseModule lifecycle:
- `attach(robot)` - Called when added to Runtime, subscribes to topics
- `start()` - Called when Runtime starts
- `on_tick(dt)` - Called every Runtime tick
- `stop()` - Called when Runtime stops
- `detach()` - Called when removed from Runtime

## Design Principles

1. **Public interface** - These are the classes users should use
2. **Robot-first** - All classes take `Robot` as first argument
3. **State tracking** - Track channel registrations, gains, etc.
4. **Validation** - Check inputs before sending to MCU
5. **Convenience** - Provide helper methods (high/low, set_percent, etc.)

## Internal Access

For advanced use cases, internal HostModules can be accessed directly:

```python
# Not recommended for normal use
from robot_host.hw.gpio import GpioHostModule
from robot_host.motor.motion import MotionHostModule

# These take (bus, client) instead of Robot
module = GpioHostModule(robot.bus, robot.client)
```
