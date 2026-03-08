# MARA Platform Architecture

<div align="center">

**Modular Asynchronous Robotics Architecture**

*System-level documentation for the monorepo*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Monorepo Layout

```
mara/
├── host/                    # Python SDK, CLI, and runtime
│   └── mara_host/
├── firmware/
│   ├── mcu/                 # ESP32 motor controller firmware
│   └── cam/                 # ESP32-CAM vision firmware
├── docs/                    # Cross-cutting documentation
├── Makefile                 # Unified build commands
└── ARCHITECTURE.md          # This file
```

### Component Boundaries

| Component | Deployment | Runtime | Primary Language |
|:----------|:-----------|:--------|:-----------------|
| `host/` | Python package (`mara_host`) | Host machine (Linux/Mac/Windows) | Python 3.10+ |
| `firmware/mcu/` | ESP32 binary | ESP32 MCU (FreeRTOS) | C++17 |
| `firmware/cam/` | ESP32-CAM binary | ESP32-CAM (Arduino) | C++ |

### What Belongs Where

| Concern | Owner | Reason |
|:--------|:------|:-------|
| Protocol schema definitions | `host/mara_host/tools/schema/` | Single source, generates both sides |
| Command implementations | `firmware/mcu/` receives, `host/` sends | MCU is executor |
| Telemetry emission | `firmware/mcu/` owns structure | MCU is data source |
| High-level robot APIs | `host/mara_host/api/` | Host provides developer UX |
| Control loop execution | `firmware/mcu/` (100Hz FreeRTOS task) | Real-time requirements |
| Camera streaming | `firmware/cam/` | Dedicated hardware |
| Vision preprocessing | `host/mara_host/camera/` | ML runs on host |
| Pin assignments | `host/mara_host/config/pins.json` | Host configures, firmware receives |
| Build configuration | `firmware/*/platformio.ini` | PlatformIO owns build |

---

## Source of Truth Map

This section defines **canonical ownership** for all shared concepts.

### Protocol & Commands

| Artifact | Canonical Source | Generated Outputs |
|:---------|:-----------------|:------------------|
| Command definitions | `tools/schema/commands/` | `CommandDefs.h`, `command_defs.py`, `client_commands.py` |
| Binary commands | `tools/schema/binary.py` | `BinaryCommands.h`, `binary_commands.py`, `json_to_binary.py` |
| Telemetry sections | `tools/schema/telemetry.py` | `TelemetrySections.h`, `telemetry_sections.py` |
| Version info | `tools/schema/version.py` | `Version.h`, `version.py` |
| CAN definitions | `tools/schema/can.py` | `CanDefs.h`, `can_defs_generated.py` |
| GPIO channels | `tools/schema/gpio_channels.py` | `GpioChannelDefs.h`, `gpio_channels.py` |
| Pin assignments | `pins.json` | `PinConfig.h`, `pin_config.py` |

### Regeneration

```bash
# Regenerate all artifacts from canonical sources
make generate
# or
mara generate all
```

**Rule**: Never edit generated files. Edit schema files, then regenerate.

### Frame Protocol

| Aspect | Owner | Location |
|:-------|:------|:---------|
| Frame format spec | Shared | `host/.../core/protocol.py`, `firmware/.../core/Protocol.h` |
| CRC algorithm | Shared | CRC16-CCITT (0x1021, init 0xFFFF) |
| Message types | `tools/schema/` | Generated to both sides |

Frame structure:
```
┌────────┬────────┬────────┬──────────┬─────────────┬──────────────┐
│ HEADER │ LEN_HI │ LEN_LO │ MSG_TYPE │   PAYLOAD   │   CRC16      │
│  0xAA  │   1B   │   1B   │    1B    │   N bytes   │    2B        │
└────────┴────────┴────────┴──────────┴─────────────┴──────────────┘
```

---

## Runtime Ownership

### Host Runtime Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            User Application                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  API Layer (api/)                  │  Services Layer (services/control/)    │
│  → Validation, exceptions          │  → Business logic, ServiceResult       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Client Layer (command/client.py)                                            │
│  → Routing, handshake, connection management                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Commander Layer (command/coms/reliable_commander.py)                        │
│  → ALL commands (reliable & streaming), ACK tracking, event emission        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Transport Layer (transport/)                                                │
│  Serial │ TCP │ CAN │ MQTT │ Bluetooth                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Ownership**:
- `Robot`: Owns transport initialization and module composition
- `API`: Owns validation and user-facing exceptions
- `Services`: Owns business logic and state tracking
- `Client`: Owns routing and handshake
- `Commander`: Owns command dispatch (single chokepoint for all commands)
- `Transport`: Owns physical connection and frame I/O

### MCU Runtime Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  main.cpp / setup() / loop()                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Runtime (core/Runtime)                                                      │
│  → Module orchestration            │  → Setup sequencing                    │
├──────────────────────────┬──────────────────────────────────────────────────┤
│  MessageRouter           │  HandlerRegistry / CommandRegistry               │
│  → Frame dispatch        │  → Command routing                               │
├──────────────────────────┴──────────────────────────────────────────────────┤
│  ModuleManager                                                               │
│  → Module lifecycle                │  → Loop coordination                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Control Task (FreeRTOS, 100Hz, Core 1)                                      │
│  → SignalBus                       │  → ControlKernel                       │
│  → MotionController                │  → Observer                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Managers (motor/, sensor/)                                                  │
│  DcMotor │ Servo │ Stepper │ Encoder │ IMU │ Ultrasonic                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  HAL (hal/)                                                                  │
│  IGpio │ IPwm │ II2c │ ITimer │ IWatchdog                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Transport Layer                                                             │
│  UART │ WiFi │ BLE │ MQTT │ CAN                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Ownership**:
- `Runtime`: Owns boot sequence and module registration
- `MessageRouter`: Owns frame parsing and event dispatch
- `HandlerRegistry`: Owns command-to-handler mapping
- `ModuleManager`: Owns module lifecycle
- `Control Task`: Owns real-time control loop (pinned to Core 1)
- `HAL`: Owns hardware abstraction for portability

---

## Integration Contracts

### Host ↔ MCU Contract

1. **Discovery**: Host sends `MSG_VERSION_REQUEST`, MCU responds with capabilities
2. **Handshake**: Protocol version must match exactly
3. **Commands**: Host sends JSON (`MSG_CMD_JSON`) or binary (`MSG_CMD_BIN`)
4. **ACKs**: MCU responds with `{type: "ACK", cmd: "...", seq: N, ok: bool}`
5. **Telemetry**: MCU streams `MSG_TELEMETRY_BIN` at configured rate
6. **Heartbeat**: Both sides emit heartbeats; timeout = disconnect

### Host ↔ CAM Contract

1. **Discovery**: Host HTTP GET to `/status`
2. **Configuration**: HTTP POST to `/control` with JSON settings
3. **Streaming**: MJPEG stream on port 81 (`/stream`)
4. **Frames**: Host polls `/capture` for single frames
5. **Independence**: CAM does not require MCU connection

---

## Feature Flag Architecture (MCU)

The MCU firmware uses compile-time feature flags for binary size optimization.

### Available Flags

| Flag | Default | Description |
|:-----|:--------|:------------|
| `HAS_WIFI` | 1 | WiFi transport |
| `HAS_BLE` | 0 | Bluetooth Classic |
| `HAS_DC_MOTOR` | 1 | DC motor control |
| `HAS_SERVO` | 1 | Servo control |
| `HAS_STEPPER` | 0 | Stepper control |
| `HAS_ENCODER` | 1 | Quadrature encoders |
| `HAS_IMU` | 1 | MPU6050 IMU |
| `HAS_SIGNAL_BUS` | 1 | Real-time signal routing |
| `HAS_CONTROL_KERNEL` | 1 | State-space control |
| `HAS_OBSERVER` | 1 | State estimation |
| `HAS_TELEMETRY` | 1 | Telemetry streaming |

### Build Profiles

| Profile | Features | Flash Size |
|:--------|:---------|:-----------|
| `esp32_minimal` | UART only | ~350KB |
| `esp32_motors` | Motors + encoders | ~550KB |
| `esp32_control` | Full control system | ~750KB |
| `esp32_full` | Everything | ~870KB |

---

## Testing Strategy

### Unit Tests

| Layer | Framework | Command |
|:------|:----------|:--------|
| Host Python | pytest | `make test-host` |
| MCU C++ | PlatformIO Unity | `make test-mcu` |

### Integration Tests

| Test Type | Location | Description |
|:----------|:---------|:------------|
| Protocol interop | `tests/test_protocol.py` | Frame encoding matches C++ |
| Telemetry parsing | `tests/test_telemetry_*.py` | Binary parser matches MCU output |
| HIL tests | `tests/test_hil_*.py` | End-to-end with real hardware |

### Recommended CI Pipeline

```yaml
steps:
  - make test-host      # Python unit tests
  - make test-mcu       # Native firmware tests
  - make generate       # Regenerate artifacts
  - git diff --exit-code  # Verify no drift
  - make build          # Build all firmware
```

---

## Glossary

| Term | Definition |
|:-----|:-----------|
| **Host** | The Python runtime on developer's machine |
| **MCU** | The ESP32 motor controller target |
| **CAM** | The ESP32-CAM vision target |
| **Transport** | Communication layer (Serial, TCP, CAN, MQTT, BLE) |
| **Frame** | A protocol message with header, payload, and CRC |
| **Handler** | MCU-side command processor |
| **Service** | Host-side business logic with ServiceResult |
| **API** | Host-side user-facing interface with validation |
| **Commander** | Single chokepoint for all command dispatch |
| **SignalBus** | Real-time value routing system on MCU |

---

## Quick Reference

```bash
# Install
make install

# Build all
make build

# Test all
make test

# Generate protocol artifacts
make generate

# Flash MCU
make flash-mcu

# Connect via CLI
mara run serial --port /dev/ttyUSB0

# Run hardware tests
mara test all --port /dev/ttyUSB0
```

---

<div align="center">

*This document is the canonical system architecture reference*

</div>
