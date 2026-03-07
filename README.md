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
| **Host** | `mara_host` (this repo) | Python async client, telemetry, research tools |

This repository contains the **Python host library** - a comprehensive async framework for controlling ESP32-based robots. Provides transport abstraction, command handling, telemetry processing, and research tools for robotics development.

## Key Features

- **Transport Layer**: Serial (USB), TCP (WiFi), Bluetooth Classic, **MQTT**
- **Multi-Node**: Control multiple ESP32 robots over MQTT with fleet discovery
- **Async Client**: Non-blocking robot control with reliable command delivery
- **Telemetry**: Real-time sensor data processing (IMU, encoders, motors)
- **Camera Module**: ESP32-CAM integration with streaming, presets, ML preprocessing
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
        await drive.turn(90)

        await robot.disarm()

asyncio.run(main())
```

### With Configuration

```python
from mara_host.config import RobotConfig

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
from mara_host import Robot
from mara_host.runtime import Runtime

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
│  │          Serial  │  TCP  │  Bluetooth  │  MQTT              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
mara_host/
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
├── module/          # Device modules
│   └── camera/            # ESP32-CAM integration
│       ├── host_module.py # CameraHostModule
│       ├── models.py      # Data models
│       └── presets.py     # Camera presets
├── mqtt/            # MQTT multi-node control
│   ├── node_manager.py    # NodeManager
│   ├── node_proxy.py      # Per-node proxy
│   ├── discovery.py       # Fleet discovery
│   ├── transport.py       # MQTT transport
│   └── broker_failover.py # Failover support
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

### Camera Demo

```bash
# Run camera demo with ESP32-CAM
python -m mara_host.runners.run_camera_host http://10.0.0.66
```

### MQTT Multi-Node

```bash
# Discover and control multiple ESP32 nodes over MQTT
python -m mara_host.runners.run_mqtt_nodes --broker 10.0.0.59

# Test with mock nodes (no hardware required)
python -m mara_host.tools.mock_node --node-id node1 --broker 10.0.0.59
```

### Robot Examples

```bash
cd examples
python 01_serial_connection.py /dev/ttyUSB0
```

## Research Module

The research module provides tools for robotics analysis:

### Simulation

```python
from mara_host.research.config_loader import load_robot

# Load robot from YAML config
robot = load_robot("mara_host/research/configs/medium_robot.yaml")

# Run simulation
for _ in range(1000):
    robot.set_velocity(0.3, 0.1)
    state = robot.step(0.01)  # 10ms step
    print(f"Position: ({state['x']:.3f}, {state['y']:.3f})")
```

### System Identification

```python
from mara_host.research.sysid import identify_first_order_step

# Estimate system parameters from step response
params = identify_first_order_step(times, response, input_amplitude=1.0)
print(f"Time constant: {params.tau} s, DC gain: {params.K}")
```

### Metrics Analysis

```python
from mara_host.research.metrics import analyze_session

# Analyze recorded session
metrics = analyze_session("session.jsonl")
print(f"Latency p95: {metrics.latency.p95_ms:.1f} ms")
print(f"Jitter: {metrics.jitter.jitter_ms:.2f} ms")
```

See `mara_host/research/README.md` for detailed research module documentation.

## Camera Module

Integrates ESP32-CAM into the robot host architecture for vision-based robotics.

### Basic Usage

```python
from mara_host.core.event_bus import EventBus
from mara_host.camera import CameraHostModule

bus = EventBus()
camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

# Subscribe to frames
bus.subscribe("camera.frame.0", lambda f: print(f"Frame: {f.data.shape}"))
bus.subscribe("camera.ml_frame.0", lambda f: print(f"ML: {f.data.shape}"))

# Start streaming
bus.publish("cmd.camera", {
    "cmd": "CMD_CAM_START_CAPTURE",
    "camera_id": 0,
    "mode": "streaming",
})

# Apply presets
bus.publish("cmd.camera", {
    "cmd": "CMD_CAM_APPLY_PRESET",
    "camera_id": 0,
    "preset": "night",  # or: fast, high_quality, ml_inference, surveillance, bright
})
```

### Features

| Feature | Description |
|---------|-------------|
| MJPEG Streaming | ~15 FPS via port 81 |
| ML Preprocessing | 224x224, ImageNet normalized, CHW format |
| 9 Presets | Optimized for streaming, night, ML, surveillance, etc. |
| Multi-Camera | Support for multiple ESP32-CAMs |
| Recording | Save frames as video or images |
| Runtime Control | Resolution, quality, brightness, contrast, exposure, gain |

### Camera Topics

| Topic | Description |
|-------|-------------|
| `cmd.camera` | Send commands |
| `camera.frame.<id>` | BGR image frames |
| `camera.ml_frame.<id>` | ML-ready preprocessed frames |
| `camera.status.<id>` | Device status |

See `mara_host/module/camera/README.md` for detailed camera module documentation.

## MQTT Multi-Node Module

Control multiple ESP32 robots over MQTT for fleet coordination.

### Basic Usage

```python
import asyncio
from mara_host.core.event_bus import EventBus
from mara_host.transport.mqtt import NodeManager

async def main():
    bus = EventBus()
    manager = NodeManager(
        bus=bus,
        broker_host="10.0.0.59",
        broker_port=1883,
    )

    await manager.start()

    # Discover all nodes on the network
    nodes = await manager.discover(timeout_s=5.0)
    print(f"Found {len(nodes)} node(s)")

    # Control a specific node
    node0 = manager.get_node("node0")
    if node0 and node0.is_online:
        await node0.client.arm()
        await node0.client.set_vel(vx=0.2, omega=0.0)
        await asyncio.sleep(2.0)
        await node0.client.cmd_stop()

    # Broadcast to all nodes
    await manager.broadcast_stop()

    await manager.stop()

asyncio.run(main())
```

### Features

| Feature | Description |
|---------|-------------|
| Discovery | Auto-discover nodes via `mara/fleet/discover` |
| Per-Node Control | Individual `NodeProxy` with `AsyncRobotClient` |
| Broadcasting | Send commands to all online nodes |
| Broker Failover | Automatic fallback to backup broker |
| Health Monitoring | Track online/offline status |

See `docs/MQTT.md` for detailed MQTT multi-node documentation.

## Control Design Module

Design state-space controllers and observers using scipy, then upload to the MCU.

```python
import numpy as np
from mara_host.control import (
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

Run examples: `python -m mara_host.control.examples`

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
from mara_host.core.event_bus import EventBus

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

### Camera Topics

| Topic | Data |
|-------|------|
| `cmd.camera` | Camera commands |
| `camera.frame.<id>` | CameraFrame (BGR image) |
| `camera.ml_frame.<id>` | MLFrame (224x224, normalized) |
| `camera.status.<id>` | CameraStatus (IP, RSSI, heap) |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_protocol.py -v

# Run with coverage
pytest tests/ --cov=mara_host
```

## Configuration

### Feature Flags

```python
from mara_host.config.feature_flags import FeatureFlags

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

## Code Generation (Host-MCU Interface)

MARA uses a single source of truth in `mara_host/tools/platform_schema.py` to generate matching code for both Python (Host) and C++ (MCU). This ensures the interface contract stays synchronized.

### Running Generators

```bash
cd mara_host/tools
python generate_all.py
```

### Generated Artifacts

| Schema | Python Output | C++ Output |
|--------|---------------|------------|
| `COMMANDS` | `command_defs.py`, `client_commands.py` | `CommandDefs.h` |
| `BINARY_COMMANDS` | `binary_commands.py`, `json_to_binary.py` | `BinaryCommands.h` |
| `TELEMETRY_SECTIONS` | `telemetry_sections.py` | `TelemetrySections.h` |
| `VERSION` | `version.py` | `Version.h` |
| `GPIO_CHANNELS` | `gpio_channels.py` | `GpioChannelDefs.h` |
| `pins.json` | `pin_config.py` | `PinConfig.h` |

See `docs/ADDING_COMMANDS.md` for the full workflow.

## Repository Organization

MARA is currently organized as two repositories:

| Repository | Path | Contents |
|------------|------|----------|
| **Host** | `Host/` | Python client, telemetry, research tools, codegen |
| **MCU** | `ESP32 MCU Host/` | ESP32 firmware (PlatformIO) |

The codegen in Host writes to both repositories, creating a cross-repo dependency.

**Trade-offs of current 2-repo setup:**
- (+) Independent versioning
- (+) Smaller clone size per repo
- (-) Cross-repo paths in codegen
- (-) Harder to make atomic changes across both

**Alternative: Monorepo** would simplify codegen paths and enable atomic commits, at the cost of a larger single repository with mixed Python/C++ toolchains.

## MARA Firmware

This library is designed to work with the [MARA Firmware](https://github.com/kwasblue/ESP32-MCU-Host) for ESP32.

The firmware includes a **Hardware Abstraction Layer (HAL)** that enables porting to other MCU platforms (STM32, RP2040) without changing business logic. The HAL provides platform-agnostic interfaces for GPIO, PWM, I2C, Timer, and Watchdog functionality.

## License

MIT License
