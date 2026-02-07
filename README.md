# MARA Host

```
 ███╗   ███╗ █████╗ ██████╗  █████╗
 ████╗ ████║██╔══██╗██╔══██╗██╔══██╗
 ██╔████╔██║███████║██████╔╝███████║
 ██║╚██╔╝██║██╔══██║██╔══██╗██╔══██║
 ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██║
 ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
 Modular Asynchronous Robotics Architecture
```

**Python Host Component**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

**MARA** (Modular Asynchronous Robotics Architecture) is a complete robotics control framework consisting of:

| Component | Repository | Description |
|-----------|------------|-------------|
| **Firmware** | [`ESP32 MCU Host`](../PlatformIO/Projects/ESP32%20MCU%20Host) | Real-time motor control, sensor fusion, communication |
| **Host** | `robot_host` (this repo) | Python async client, telemetry, research tools |

This repository contains the **Python host library** - a comprehensive async framework for controlling ESP32-based robots. Provides transport abstraction, command handling, telemetry processing, and research tools for robotics development.

## Key Features

- **Transport Layer**: Serial (USB), TCP (WiFi), Bluetooth Classic
- **Async Client**: Non-blocking robot control with reliable command delivery
- **Telemetry**: Real-time sensor data processing (IMU, encoders, motors)
- **Control Design**: LQR, pole placement, observer design with scipy
- **Research Tools**: Simulation, system identification, metrics analysis
- **Recording/Replay**: Session recording for offline analysis

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd Host

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Dependencies

- Python 3.10+
- pyserial
- numpy
- scipy
- matplotlib
- pandas
- pyyaml

## Quick Start

### Basic Usage

```python
import asyncio
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
        await drive.turn(90)

        await robot.disarm()

asyncio.run(main())
```

### With Configuration

```python
from robot_host.config import RobotConfig

config = RobotConfig.load("robots/my_robot.yaml", profile="bench")
errors = config.validate()
if errors:
    print(f"Config errors: {errors}")
else:
    async with config.create_robot() as robot:
        await robot.arm()
```

### With Runtime Loop

```python
from robot_host import Robot
from robot_host.runtime import Runtime

async with Robot("/dev/ttyUSB0") as robot:
    runtime = Runtime(robot, tick_hz=50.0)

    @runtime.on_tick
    async def control(dt: float):
        await robot.motion.set_velocity(0.1, 0.0)

    @runtime.on_start
    async def setup():
        await robot.arm()

    await runtime.run(duration=10.0)
```

### Receive Telemetry

```python
def on_imu(data):
    print(f"IMU: ax={data['ax']:.2f}, ay={data['ay']:.2f}")

robot.on("telemetry.imu", on_imu)
```

## Architecture

The library provides a clear layered architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Application                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   RobotConfig    │  │     Runtime      │  │     Robot     │  │
│  │  (config/)       │  │   (runtime/)     │  │  (robot.py)   │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  │
│           │                     │                    │          │
│           └─────────────────────┼────────────────────┘          │
│                                 │                               │
│  ┌──────────────────────────────┴─────────────────────────────┐ │
│  │                    Public API (api/)                        │ │
│  │  GPIO, PWM, DifferentialDrive, PIDController, Encoder, ... │ │
│  └──────────────────────────────┬─────────────────────────────┘ │
│                                 │                               │
├─────────────────────────────────┼───────────────────────────────┤
│                                 │  INTERNAL                     │
│  ┌──────────────────────────────┴─────────────────────────────┐ │
│  │              HostModules (hw/, motor/, sensor/)             │ │
│  │         GpioHostModule, MotionHostModule, etc.              │ │
│  └──────────────────────────────┬─────────────────────────────┘ │
│                                 │                               │
│  ┌──────────────────────────────┴─────────────────────────────┐ │
│  │              AsyncRobotClient + EventBus                    │ │
│  └──────────────────────────────┬─────────────────────────────┘ │
│                                 │                               │
│  ┌──────────────────────────────┴─────────────────────────────┐ │
│  │                    Transport Layer                          │ │
│  │              Serial  │  TCP  │  Bluetooth                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
robot_host/
├── config/          # Configuration
│   ├── feature_flags.py   # Feature flag definitions
│   ├── command_defs.py    # Command definitions
│   └── pin_config.py      # Pin mappings
├── core/            # Core components
│   ├── event_bus.py       # Pub/sub messaging
│   ├── protocol.py        # Frame protocol
│   └── messages.py        # Message types
├── transport/       # Communication transports
│   ├── serial_transport.py
│   ├── tcp_transport.py
│   └── bluetooth_transport.py
├── command/         # Command handling
│   ├── client.py          # AsyncRobotClient
│   └── coms/
│       ├── reliable_commander.py
│       └── connection_monitor.py
├── telemetry/       # Telemetry processing
│   ├── parser.py          # Telemetry parsing
│   ├── models.py          # Data models
│   └── host_module.py     # Telemetry module
├── motor/           # Motor modules
│   ├── motion.py          # MotionHostModule
│   ├── servo.py
│   └── stepper.py
├── sensor/          # Sensor modules
│   ├── encoder.py         # EncoderHostModule
│   ├── imu.py
│   └── ultrasonic.py
├── hw/              # Hardware modules
│   ├── gpio.py            # GpioHostModule
│   └── pwm.py
├── control/         # Control design tools
│   ├── state_space.py     # StateSpaceModel class
│   ├── design.py          # LQR, pole placement, observer
│   ├── upload.py          # MCU upload helpers
│   └── examples.py        # Usage examples
├── research/        # Research & analysis tools
│   ├── simulation.py      # Physics simulation
│   ├── sysid.py           # System identification
│   ├── metrics.py         # Performance metrics
│   ├── analysis.py        # Signal analysis
│   ├── plotting.py        # Visualization
│   ├── recording.py       # Session recording
│   ├── replay.py          # Session replay
│   └── configs/           # Robot configurations
└── examples/        # Example scripts
```

## Examples

See the `examples/` directory for comprehensive examples:

| Example | Description |
|---------|-------------|
| `01_serial_connection.py` | USB serial connection |
| `02_tcp_connection.py` | WiFi TCP connection |
| `03_command_basics.py` | Sending commands, ACKs |
| `04_telemetry_stream.py` | Receiving sensor data |
| `05_gpio_control.py` | GPIO control (LEDs) |
| `06_motor_control.py` | Motor velocity control |
| `07_encoder_feedback.py` | Encoder reading |
| `08_session_recording.py` | Recording sessions |
| `09_full_robot_control.py` | Complete control loop |

```bash
cd examples
python 01_serial_connection.py /dev/ttyUSB0
```

## Research Module

The research module provides tools for robotics analysis:

### Simulation

```python
from robot_host.research.config_loader import load_robot

# Load robot from YAML config
robot = load_robot("robot_host/research/configs/medium_robot.yaml")

# Run simulation
for _ in range(1000):
    robot.set_velocity(0.3, 0.1)
    state = robot.step(0.01)  # 10ms step
    print(f"Position: ({state['x']:.3f}, {state['y']:.3f})")
```

### System Identification

```python
from robot_host.research.sysid import identify_first_order_step

# Estimate system parameters from step response
params = identify_first_order_step(times, response, input_amplitude=1.0)
print(f"Time constant: {params.tau} s, DC gain: {params.K}")
```

### Metrics Analysis

```python
from robot_host.research.metrics import analyze_session

# Analyze recorded session
metrics = analyze_session("session.jsonl")
print(f"Latency p95: {metrics.latency.p95_ms:.1f} ms")
print(f"Jitter: {metrics.jitter.jitter_ms:.2f} ms")
```

See `robot_host/research/README.md` for detailed research module documentation.

## Control Design Module

Design state-space controllers and observers using scipy, then upload to the MCU.

```python
import numpy as np
from robot_host.control import (
    StateSpaceModel, lqr, observer_gains, configure_state_feedback
)

# Define system (mass-spring-damper)
A = np.array([[0, 1], [-10, -0.5]])
B = np.array([[0], [1]])
C = np.array([[1, 0]])
model = StateSpaceModel(A, B, C)

# Check system properties
print(f"Controllable: {model.is_controllable()}")
print(f"Observable: {model.is_observable()}")
print(f"Open-loop poles: {model.poles}")

# Design LQR controller
Q = np.diag([100, 1])  # State cost
R = np.array([[1]])    # Control cost
K, S, E = lqr(A, B, Q, R)
print(f"LQR gain K: {K}")
print(f"Closed-loop poles: {E}")

# Design observer (faster than controller)
L = observer_gains(A, C, poles=[-25, -30])

# Upload to MCU
result = await configure_state_feedback(
    client, model, K,
    L=L,
    use_observer=True,
    signals={
        "state": [10, 11],
        "ref": [12, 13],
        "control": [20],
        "measurement": [30],
    },
)
```

Run examples: `python -m robot_host.control.examples`

See `docs/ADDING_COMMANDS.md` for full documentation.

## API Reference

### AsyncRobotClient

Main client class for robot control.

```python
client = AsyncRobotClient(
    transport=transport,
    bus=EventBus(),
    heartbeat_interval_s=0.2,
    connection_timeout_s=1.0,
    command_timeout_s=0.25,
    max_retries=3,
)

# Lifecycle
await client.start()
await client.stop()

# State machine
await client.arm()
await client.disarm()
await client.activate()
await client.deactivate()
await client.estop()
await client.clear_estop()

# Motion
await client.set_vel(vx=0.2, omega=0.1)
await client.cmd_stop()

# Reliable commands
success, error = await client.send_reliable("CMD_NAME", {"key": "value"})

# Properties
client.is_connected
client.robot_name
client.firmware_version
```

### EventBus

Pub/sub messaging for telemetry and events.

```python
from robot_host.core.event_bus import EventBus

bus = EventBus()

# Subscribe to topics
def handler(data):
    print(data)

bus.subscribe("telemetry.imu", handler)

# Publish events
bus.publish("telemetry.imu", {"ax": 0.1, "ay": 0.0, "az": 9.8})
```

### Telemetry Topics

| Topic | Data |
|-------|------|
| `telemetry.raw` | Raw telemetry JSON |
| `telemetry.packet` | Parsed TelemetryPacket |
| `telemetry.imu` | IMU data (ax, ay, az, gx, gy, gz) |
| `telemetry.encoder0` | Encoder ticks/velocity |
| `telemetry.dc_motor0` | Motor PWM/current |
| `telemetry.ultrasonic` | Distance reading |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_protocol.py -v

# Run with coverage
pytest tests/ --cov=robot_host
```

## Configuration

### Feature Flags

```python
from robot_host.config.feature_flags import FeatureFlags

# Get preset configurations
flags = FeatureFlags.minimal()   # UART only
flags = FeatureFlags.motors()    # Motors + encoders
flags = FeatureFlags.sensors()   # WiFi + sensors
flags = FeatureFlags.full()      # Everything
```

### Robot Configuration (YAML)

```yaml
name: my_robot
type: diff_drive

drive:
  wheel_radius: 0.05      # meters
  wheel_base: 0.2         # meters
  max_linear_vel: 1.0     # m/s
  max_angular_vel: 3.0    # rad/s

noise:
  imu:
    accel_std: 0.01       # g
    gyro_std: 0.001       # rad/s
  encoder:
    counts_per_rev: 1000

simulation:
  dt: 0.01                # seconds
```

## Performance

| Metric | Value |
|--------|-------|
| Command latency | < 5ms (local) |
| Telemetry rate | 50+ Hz |
| Frame parsing | O(n) optimized |
| Memory stable | Bounded queues |

## MARA Firmware

This library is designed to work with the [MARA Firmware](../PlatformIO/Projects/ESP32%20MCU%20Host) for ESP32.

## License

MIT License
