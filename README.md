# MARA - Modular Asynchronous Robotics Architecture

```
 ███╗   ███╗ █████╗ ██████╗  █████╗
 ████╗ ████║██╔══██╗██╔══██╗██╔══██╗
 ██╔████╔██║███████║██████╔╝███████║
 ██║╚██╔╝██║██╔══██║██╔══██╗██╔══██║
 ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██║
 ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
 Modular Asynchronous Robotics Architecture
```

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PlatformIO](https://img.shields.io/badge/PlatformIO-ESP32-orange.svg)](https://platformio.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**A complete robotics platform combining Python host software with ESP32 firmware.**

---

## Overview

MARA is a unified monorepo containing everything needed for ESP32-based robotics:

| Component | Location | Description |
|-----------|----------|-------------|
| **Host** | `host/` | Python async client, CLI, telemetry, research tools |
| **MCU Firmware** | `firmware/mcu/` | ESP32 motor control, sensors, real-time control |
| **CAM Firmware** | `firmware/cam/` | ESP32-CAM streaming, motion detection, REST API |

## Repository Structure

```
mara/
├── host/                    # Python host package (mara_host)
│   ├── mara_host/           # Core library
│   │   ├── api/             # High-level APIs (motor, servo, encoder, etc.)
│   │   ├── cli/             # Command-line interface
│   │   │   └── commands/    # CLI command packages
│   │   │       ├── calibrate/
│   │   │       ├── pins/
│   │   │       ├── run/
│   │   │       └── test/
│   │   ├── command/         # Client, factory, protocol
│   │   ├── services/        # Business logic (pins, codegen, testing)
│   │   ├── transport/       # Serial, TCP, CAN, MQTT, Bluetooth
│   │   ├── research/        # Simulation, sysid, metrics
│   │   └── camera/          # ESP32-CAM integration
│   └── tests/               # Python tests
│
├── firmware/
│   ├── mcu/                 # ESP32 MCU firmware
│   │   ├── src/             # C++ source files
│   │   │   ├── command/     # Command handlers
│   │   │   ├── control/     # PID, state-space, observers
│   │   │   ├── motor/       # DC, stepper, servo drivers
│   │   │   ├── sensor/      # Encoder, IMU, ultrasonic
│   │   │   └── transport/   # Serial, WiFi, MQTT
│   │   ├── include/         # Header files
│   │   └── platformio.ini   # Build configurations
│   │
│   └── cam/                 # ESP32-CAM firmware
│       ├── src/             # Camera, streaming, web server
│       ├── include/         # Headers
│       └── platformio.ini   # Build configuration
│
├── protocol/                # Shared protocol definitions
├── tools/                   # Unified build/flash scripts
├── docs/                    # Documentation
│   └── architecture/        # Architecture docs
└── Makefile                 # Unified build commands
```

## Quick Start

### Prerequisites

- Python 3.10+
- PlatformIO Core (`pip install platformio`)
- ESP32 development board(s)

### Installation

```bash
# Clone the repository
git clone https://github.com/kwasblue/mara.git
cd mara

# Install the Python host package
make install

# Or with development dependencies
make install-dev
```

### Building Firmware

```bash
# Build all firmware
make build

# Build specific targets
make build-mcu          # Main MCU firmware
make build-cam          # Camera firmware

# Build MCU with specific feature set
make build-mcu-minimal  # UART only, ~350KB
make build-mcu-motors   # Motor control, ~550KB
make build-mcu-control  # Full control system, ~750KB
make build-mcu-full     # All features, ~870KB
```

### Flashing

```bash
# Flash MCU firmware (configure port in platformio.ini)
make flash-mcu

# Flash CAM firmware
make flash-cam
```

### Using the CLI

```bash
# Connect via serial
mara run serial --port /dev/ttyUSB0

# Run hardware tests
mara test commands --port /dev/ttyUSB0

# Pin management
mara pins list
mara pins wizard motor
mara pins suggest pwm

# Calibration wizards
mara calibrate motor
mara calibrate encoder
mara calibrate pid
```

## Components

### Host (`host/mara_host/`)

The Python host package provides:

- **CLI** (`mara`): Full-featured command-line interface
  - `mara run` - Connect via serial/TCP/CAN/MQTT
  - `mara test` - Hardware validation tests
  - `mara calibrate` - Motor/encoder/PID calibration
  - `mara pins` - GPIO pin management and wizards
  - `mara generate` - Code generation
  - `mara record` / `mara replay` - Session recording
  - `mara mqtt` - MQTT broker management
  - `mara build` / `mara flash` - Firmware build and flash
  - `mara monitor` - Live telemetry dashboard
  - `mara logs` - View recorded sessions
  - `mara sim` - Launch simulation mode

- **API**: High-level Python APIs
  - `GPIO`, `PWM` - Hardware control
  - `DifferentialDrive` - Motion control
  - `PIDController` - Velocity control
  - `Encoder`, `IMU`, `Ultrasonic` - Sensor access

- **Transports**: Multiple connectivity options
  - Serial (USB)
  - TCP (WiFi)
  - CAN bus
  - MQTT (multi-node fleet control)
  - Bluetooth Classic

- **Services**: Business logic layer
  - `PinService` - Pin management with conflict detection
  - `TestService` - Hardware validation
  - `RecordingService` - Session recording/replay
  - `GeneratorService` - Code generation

- **Research**: Analysis tools
  - Physics simulation
  - System identification
  - Control design (LQR, pole placement)
  - Metrics and plotting

### MCU Firmware (`firmware/mcu/`)

ESP32 firmware using the `mara::` namespace:

- **Motor Control**
  - DC motors with velocity PID
  - Stepper motors (position/velocity)
  - Servo motors

- **Sensors**
  - Quadrature encoders
  - IMU (accelerometer + gyroscope)
  - Ultrasonic distance

- **Control Systems**
  - SignalBus - real-time signal routing
  - ControlKernel - state-space controllers
  - Observers - Luenberger state estimation

- **Communication**
  - JSON command protocol
  - Binary telemetry
  - Reliable ACK/retry

- **Feature Flags**
  - Compile-time feature selection
  - Multiple build profiles (minimal → full)

### CAM Firmware (`firmware/cam/`)

ESP32-CAM firmware for vision:

- **Camera Control**
  - OV2640 sensor with 30+ settings
  - Resolution presets (VGA, QVGA, etc.)
  - Quality, brightness, contrast, exposure

- **Streaming**
  - MJPEG streaming at up to 30fps
  - Up to 3 concurrent clients
  - Adaptive quality under load

- **Motion Detection**
  - Frame-based detection
  - Configurable sensitivity
  - Callback mechanism

- **Web Interface**
  - REST API for configuration
  - Captive portal for WiFi setup
  - OTA firmware updates
  - HTTP Basic Auth + rate limiting

## Examples

### Basic Robot Control

```python
import asyncio
from mara_host import Robot, GPIO, DifferentialDrive

async def main():
    async with Robot("/dev/ttyUSB0") as robot:
        await robot.arm()

        # Control GPIO
        gpio = GPIO(robot)
        await gpio.register(0, pin=2, mode="output")
        await gpio.high(0)

        # Drive
        drive = DifferentialDrive(robot)
        await drive.drive_straight(1.0, speed=0.3)
        await drive.turn(90)

        await robot.disarm()

asyncio.run(main())
```

### Multi-Node Fleet Control (MQTT)

```python
from mara_host.transport.mqtt import NodeManager

async def main():
    manager = NodeManager(broker_host="10.0.0.59")
    await manager.start()

    # Discover all robots
    nodes = await manager.discover(timeout_s=5.0)
    print(f"Found {len(nodes)} robots")

    # Control specific robot
    robot = manager.get_node("robot_1")
    if robot and robot.is_online:
        await robot.client.arm()
        await robot.client.set_vel(vx=0.2, omega=0.0)

    # Broadcast stop to all
    await manager.broadcast_stop()

asyncio.run(main())
```

### Camera Streaming

```python
from mara_host.camera import CameraHostModule

camera = CameraHostModule(cameras={0: "http://10.0.0.66"})

# Subscribe to frames
@camera.on_frame
def handle_frame(frame):
    print(f"Frame: {frame.shape}")

# Start streaming
await camera.start_capture(0, mode="streaming")

# Apply preset
await camera.apply_preset(0, "night")
```

## Testing

```bash
# Run all tests
make test

# Run host tests only
make test-host

# Run MCU native tests
make test-mcu

# Run specific test file
cd host && pytest tests/test_protocol.py -v
```

### Hardware-in-the-Loop (HIL) Testing

Run tests against real hardware:

```bash
# Run all HIL tests (TCP + serial)
# Defaults: MCU_PORT=/dev/cu.usbserial-0001, ROBOT_HOST=10.0.0.60
make test-hil

# Override defaults
MCU_PORT=/dev/ttyUSB0 ROBOT_HOST=192.168.1.100 make test-hil

# Serial-only tests
make test-hil-serial
```

### MQTT Broker

For WiFi-connected robots, start a local MQTT broker:

```bash
# Start broker (runs in background)
mara mqtt start

# Check status
mara mqtt status

# Stop broker
mara mqtt stop

# Run in foreground (for debugging)
mara mqtt start -f
```

The broker listens on all interfaces, allowing ESP32 devices to connect via WiFi.

## Architecture Philosophy

### Host-Firmware Parity
Protocol changes are atomic - a single commit updates both Python definitions and C++ handlers, preventing version drift.

### Feature Flags
MCU firmware uses compile-time feature selection. Enable only what you need:
```ini
# platformio.ini
build_flags = -DHAS_DC_MOTOR=1 -DHAS_ENCODER=1 -DHAS_IMU=0
```

### Service Layer
Business logic is separated from CLI presentation:
```
CLI Command → Service → Client → Transport → MCU
```

### Package Domains
Clear boundaries between domains:
- `motor/` - Motor control
- `sensor/` - Sensor integration
- `transport/` - Communication
- `control/` - Control systems
- `command/` - Protocol handling

## Code Generation

The codebase uses code generation to keep host and firmware in sync:

```bash
# Generate all code
make generate

# Or via CLI
mara generate all

# Generate specific artifacts
mara generate commands   # Command definitions
mara generate pins       # Pin configuration
mara generate telemetry  # Telemetry sections
```

### Generated Artifacts

| Source | Python Output | C++ Output |
|--------|---------------|------------|
| `commands.json` | `command_defs.py` | `CommandDefs.h` |
| `pins.json` | `pin_config.py` | `PinConfig.h` |
| `TELEMETRY_SECTIONS` | `telemetry_sections.py` | `TelemetrySections.h` |

## Documentation

- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Build your first robot
- [Architecture Overview](docs/architecture/ARCHITECTURE.md)
- [Host API Reference](host/mara_host/api/README.md)
- [MCU Firmware Guide](firmware/mcu/README.md)
- [MQTT Multi-Robot Guide](docs/MQTT.md)
- [Code Generation](docs/CODEGEN.md)
- [Camera Module](host/mara_host/camera/README.md)
- [Research Tools](host/mara_host/research/README.md)

## Performance

| Metric | Value |
|--------|-------|
| Command latency | < 5ms (USB serial) |
| Telemetry rate | 50-100 Hz |
| Control loop | 100 Hz (FreeRTOS) |
| MJPEG streaming | ~15-30 fps |

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Authors

- Kwasi Addo
