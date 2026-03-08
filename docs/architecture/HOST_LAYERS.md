# MARA Host Architecture

This document defines the host-side architecture for MARA robotics platform.

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  gui/          - Qt desktop application                         │
│  cli/          - Command-line interface                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  workflows/    - Multi-step orchestrated operations             │
│  runtime/      - Control loop and module lifecycle              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                               │
│  services/     - Single-domain business operations              │
│  api/          - User-facing object model (Stepper, GPIO, etc.) │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                          │
│  command/      - Wire protocol client                           │
│  transport/    - Serial/TCP transports                          │
│  core/         - Protocol encoding, events, base classes        │
│  telemetry/    - Binary telemetry parsing                       │
└─────────────────────────────────────────────────────────────────┘
```

## Preferred Public Paths

Choose the right entry point based on your use case:

| Use Case | Entry Point | Example |
|----------|-------------|---------|
| **Casual scripting** | `Robot` facade | `async with Robot("/dev/ttyUSB0") as robot: await robot.arm()` |
| **Object-oriented control** | `api/` classes | `gpio = GPIO(robot); await gpio.high(0)` |
| **Service-level operations** | `services/` | `state_svc = StateService(client); await state_svc.arm()` |
| **Multi-step automation** | `workflows/` | `workflow = MotorCalibrationWorkflow(client); await workflow.run()` |
| **Control loops** | `Runtime` | `runtime = Runtime(robot); await runtime.run()` |
| **GUI application** | `gui/` | `mara gui` |
| **CLI automation** | `cli/` | `mara connect && mara arm` |

## Package Responsibilities

### Presentation Layer

**gui/** - Qt Desktop Application
- Thin panels that compose widgets and wire signals
- `RobotController` delegates to services (no business logic)
- `widgets/` provides reusable UI components
- Runs async operations via dedicated event loop thread

**cli/** - Command-Line Interface
- Thin commands that invoke services or workflows
- Progress display and user interaction
- Configuration management

### Application Layer

**workflows/** - Orchestrated Operations
- Multi-step operations with progress, cancellation, and results
- Reusable from CLI, GUI, or scripts
- Examples: `MotorCalibrationWorkflow`, `SmokeTestWorkflow`, `RecordingWorkflow`
- Uses `WorkflowResult` for consistent return values

**runtime/** - Control Loop
- `Runtime` class for tick-based control loops
- Module lifecycle management
- Event-driven architecture with `BaseModule`

### Domain Layer

**services/** - Domain Services
- Single-concern business operations
- `StateService` - arm/disarm/estop
- `MotionService` - velocity control
- `MotorService`, `ServoService`, `GpioService` - hardware control
- `TelemetryService` - data subscription
- `ConnectionService` - transport management
- Uses `ServiceResult` for consistent return values

**api/** - User Object Model
- High-level abstractions for hardware
- `Stepper`, `Servo`, `DCMotor` - actuators
- `Encoder`, `IMU`, `Ultrasonic` - sensors
- `GPIO`, `PWM` - I/O
- `DifferentialDrive`, `VelocityController` - control

### Infrastructure Layer

**command/** - Protocol Client
- `MaraClient` - reliable and fast command sending
- `BinaryProtocol` - framing and CRC
- JSON-to-binary conversion

**transport/** - Transport Layer
- `SerialTransport` - UART communication
- `TcpTransport` - Network communication
- Connection management

**core/** - Foundation
- `EventBus` - pub/sub events
- `BaseModule` - module base class
- Protocol encoding/decoding
- Settings and configuration types

**telemetry/** - Telemetry Parsing
- Binary telemetry frame parsing
- Section definitions
- IMU, encoder, state data structures

### Support Packages

**config/** - Configuration
- `RobotConfig` - YAML robot definitions
- Command definitions and schemas

**tools/** - Code Generation
- Schema definitions
- Generator scripts
- Development utilities

**research/** - Experiments
- Simulation
- Recording analysis
- Prototyping

## Camera Subsystem

The camera is a **first-class MARA subsystem** running on separate hardware (ESP32-CAM).

### Architecture Decision

The camera subsystem is treated as an integrated part of MARA because:
1. It follows the same architectural patterns (EventBus, services, GUI panels)
2. It's a natural extension for robotics applications (vision, navigation)
3. The hardware separation (WiFi vs serial) is an implementation detail

### Hardware Topology

```
┌─────────────────┐         ┌─────────────────┐
│   Host (PC)     │         │   Main MCU      │
│                 │  Serial │   (ESP32)       │
│  mara_host      │◄───────►│  firmware/mcu   │
│                 │         │                 │
│  camera/        │         │  Motors, GPIO   │
│  services/cam   │  WiFi   │  Sensors, etc.  │
└────────┬────────┘         └─────────────────┘
         │
         │ HTTP/MJPEG
         ▼
┌─────────────────┐
│   Camera MCU    │
│   (ESP32-CAM)   │
│  firmware/cam   │
│                 │
│  MJPEG stream   │
│  Motion detect  │
└─────────────────┘
```

### Host-Side Components

| Package | Purpose |
|---------|---------|
| `camera/` | Client library (sync, async, streaming) |
| `camera/host_module.py` | EventBus integration |
| `camera/recorder.py` | Frame recording |
| `services/camera/` | StreamService, CameraControlService |
| `gui/panels/camera.py` | Camera panel |

### Firmware (`firmware/cam/`)

Separate PlatformIO project for ESP32-CAM with:
- MJPEG streaming server
- Motion detection
- Web configuration UI
- OTA updates
- WiFi management

### Installation

Camera requires vision dependencies (optional):
```bash
pip install mara-host[vision]  # Adds numpy, opencv-python
```

### Usage Pattern

```python
from mara_host import Robot
from mara_host.camera import CameraHostModule

async with Robot("/dev/ttyUSB0") as robot:
    # Add camera to event bus
    camera = CameraHostModule(robot._bus, cameras={0: "http://10.0.0.66"})

    # Subscribe to frames
    robot._bus.subscribe("camera.frame.0", process_frame)

    # Control via events
    robot._bus.publish("cmd.camera", {
        "cmd": "CMD_CAM_START_CAPTURE",
        "camera_id": 0
    })
```

## Dependency Rules

```
gui/ cli/           → workflows/, services/, api/, Robot
    ↓
workflows/          → services/, command/
    ↓
services/           → command/, config/, tools/
    ↓
api/                → command/, core/
    ↓
command/            → transport/, core/
    ↓
transport/ core/    → (no internal dependencies)
```

**Key constraints:**
- `services/` must NOT depend on `cli/`, `gui/`, or `runtime/`
- `workflows/` must NOT depend on `cli/` or `gui/`
- `api/` must NOT depend on `services/` (parallel layer)
- Presentation layers may use both `api/` and `services/`

## Adding New Features

### New Hardware Support
1. Add firmware command in `config/commands.json`
2. Create API class in `api/` (e.g., `api/lidar.py`)
3. Add service if complex operations needed
4. Export from `__init__.py`

### New Workflow
1. Create in `workflows/<category>/`
2. Extend `BaseWorkflow`
3. Implement `run()` method
4. Use `_emit_progress()` for progress updates
5. Return `WorkflowResult`

### New GUI Panel
1. Create thin panel in `gui/panels/`
2. Use widgets from `gui/widgets/`
3. Connect signals to controller methods
4. Controller delegates to services

### New CLI Command
1. Create in `cli/commands/`
2. Use services or workflows
3. Handle progress display

## Testing Strategy

| Layer | Test Location | Type |
|-------|--------------|------|
| `api/`, `services/` | `tests/test_*.py` | Unit tests with mocked client |
| `workflows/` | `tests/test_workflows.py` | Unit tests with mocked client |
| `gui/` | `tests/test_gui_panels.py` | Import tests, signal verification |
| Integration | `tests/test_hil_*.py` | Hardware-in-the-loop tests |
