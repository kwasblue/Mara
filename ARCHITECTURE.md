# MARA Platform Architecture

> Modular Asynchronous Robotics Architecture - System-Level Documentation

This document defines the canonical architecture of the MARA monorepo, establishing ownership boundaries, source-of-truth mappings, and integration contracts across all components.

---

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
└── ARCHITECTURE.md          # This file (canonical system reference)
```

### Component Boundaries

| Component | Deployment | Runtime | Primary Language |
|-----------|------------|---------|------------------|
| `host/` | Python package (`mara_host`) | Host machine (Linux/Mac/Windows) | Python 3.10+ |
| `firmware/mcu/` | ESP32 binary | ESP32 MCU (FreeRTOS) | C++17 |
| `firmware/cam/` | ESP32-CAM binary | ESP32-CAM (Arduino) | C++ |

### What Belongs Where

| Concern | Owner | Reason |
|---------|-------|--------|
| Protocol schema definitions | `host/mara_host/tools/platform_schema.py` | Single source, generates both sides |
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
|----------|------------------|-------------------|
| Command definitions | `platform_schema.py::COMMANDS` | `CommandDefs.h`, `command_defs.py`, `client_commands.py` |
| Binary commands | `platform_schema.py::BINARY_COMMANDS` | `BinaryCommands.h`, `binary_commands.py`, `json_to_binary.py` |
| Telemetry sections | `platform_schema.py::TELEMETRY_SECTIONS` | `TelemetrySections.h`, `telemetry_sections.py` |
| Version info | `platform_schema.py::VERSION` | `Version.h`, `version.py` |
| Capabilities | `platform_schema.py::CAPABILITIES` | Embedded in `Version.h` |
| CAN definitions | `platform_schema.py::CAN_*` | `CanDefs.h`, `can_defs_generated.py` |
| GPIO channels | `platform_schema.py::GPIO_CHANNELS` | `GpioChannelDefs.h`, `gpio_channels.py` |
| Pin assignments | `pins.json` | `PinConfig.h`, `pin_config.py` |

### Regeneration

```bash
# Regenerate all artifacts from canonical sources
make generate
# or
mara generate all
```

**Rule**: Never edit generated files. Edit `platform_schema.py` or `pins.json`, then regenerate.

### Frame Protocol

| Aspect | Owner | Location |
|--------|-------|----------|
| Frame format spec | Shared | `host/.../core/protocol.py`, `firmware/.../core/Protocol.h` |
| CRC algorithm | Shared | CRC16-CCITT (0x1021, init 0xFFFF) |
| Message types | `platform_schema.py` | Generated to both sides |

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
┌─────────────────────────────────────────────────────────────┐
│                    User Application                          │
├─────────────────────────────────────────────────────────────┤
│  Robot (robot.py)           │  Runtime (runtime.py)         │
│  - Connection facade        │  - Optional tick loop         │
│  - Lazy module creation     │  - Module lifecycle           │
├─────────────────────────────────────────────────────────────┤
│  MaraClient (command/client.py)                             │
│  - Protocol handling        │  - ReliableCommander          │
│  - Connection monitoring    │  - ACK/retry logic            │
├─────────────────────────────────────────────────────────────┤
│  Transport Layer (transport/)                               │
│  Serial │ TCP │ CAN │ MQTT │ Bluetooth                      │
└─────────────────────────────────────────────────────────────┘
```

**Ownership**:
- `Robot`: Owns transport initialization and module composition
- `MaraClient`: Owns protocol encoding/decoding and reliable delivery
- `Runtime`: Optional; owns tick loop when real-time control needed on host
- `Transport`: Owns physical connection and frame I/O

### MCU Runtime Stack

```
┌─────────────────────────────────────────────────────────────┐
│  main.cpp / setup() / loop()                                │
├─────────────────────────────────────────────────────────────┤
│  Runtime (core/Runtime)                                     │
│  - Module orchestration     │  - Setup sequencing           │
├──────────────────────┬──────────────────────────────────────┤
│  MessageRouter       │  HandlerRegistry / CommandRegistry   │
│  - Frame dispatch    │  - Command routing                   │
├──────────────────────┴──────────────────────────────────────┤
│  ModuleManager                                              │
│  - Module lifecycle         │  - Loop coordination          │
├─────────────────────────────────────────────────────────────┤
│  Control Task (FreeRTOS, 100Hz, Core 1)                     │
│  - SignalBus               │  - ControlKernel               │
│  - MotionController        │  - Observer                    │
├─────────────────────────────────────────────────────────────┤
│  Managers (motor/, sensor/)                                 │
│  DcMotor │ Servo │ Stepper │ Encoder │ IMU │ Ultrasonic    │
├─────────────────────────────────────────────────────────────┤
│  HAL (hal/)                                                 │
│  IGpio │ IPwm │ II2c │ ITimer │ IWatchdog                  │
├─────────────────────────────────────────────────────────────┤
│  Transport Layer                                            │
│  UART │ WiFi │ BLE │ MQTT │ CAN                            │
└─────────────────────────────────────────────────────────────┘
```

**Ownership**:
- `Runtime`: Owns boot sequence and module registration
- `MessageRouter`: Owns frame parsing and event dispatch
- `HandlerRegistry`: Owns command-to-handler mapping (extensible)
- `ModuleManager`: Owns module lifecycle (init/loop/deinit)
- `Control Task`: Owns real-time control loop (pinned to Core 1)
- `HAL`: Owns hardware abstraction for portability

### Camera Runtime Stack

```
┌─────────────────────────────────────────────────────────────┐
│  main.cpp / setup() / loop()                                │
├─────────────────────────────────────────────────────────────┤
│  Handlers (handlers/)                                       │
│  - Camera control           │  - Settings                   │
├─────────────────────────────────────────────────────────────┤
│  Camera (camera/)                                           │
│  - OV2640 control           │  - MJPEG streaming            │
├─────────────────────────────────────────────────────────────┤
│  Network (network/)                                         │
│  - WiFi                     │  - Web server                 │
│  - Captive portal           │  - REST API                   │
├─────────────────────────────────────────────────────────────┤
│  Security (security/)                                       │
│  - Auth                     │  - Rate limiting              │
└─────────────────────────────────────────────────────────────┘
```

**Ownership**:
- Camera firmware is **independent** of MCU firmware
- Communicates with host directly via HTTP/MJPEG
- Does not share runtime code with MCU

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

### Version Compatibility

```
Host sends VERSION_REQUEST
MCU responds with:
  - firmware: "1.0.0"
  - protocol: 1
  - schema_version: 1
  - capabilities: 0x000F

Host verifies:
  - protocol version matches exactly
  - capabilities include required features
```

**Breaking changes** require protocol version bump.

---

## Generated vs Manual Artifacts

### Generated Files (Never Edit)

| Directory | Files | Generator |
|-----------|-------|-----------|
| `host/mara_host/config/` | `command_defs.py`, `client_commands.py`, `version.py`, `pin_config.py`, `gpio_channels.py` | `generate_all.py` |
| `host/mara_host/command/` | `binary_commands.py`, `json_to_binary.py` | `gen_binary_commands.py` |
| `host/mara_host/telemetry/` | `telemetry_sections.py` | `gen_telemetry.py` |
| `host/mara_host/transport/` | `can_defs_generated.py` | `gen_can.py` |
| `firmware/mcu/include/config/` | `CommandDefs.h`, `Version.h`, `PinConfig.h`, `GpioChannelDefs.h`, `CanDefs.h` | `generate_all.py` |
| `firmware/mcu/include/command/` | `BinaryCommands.h` | `gen_binary_commands.py` |
| `firmware/mcu/include/telemetry/` | `TelemetrySections.h` | `gen_telemetry.py` |

### Manual Files (Edit Freely)

- All source code not listed above
- `platform_schema.py` (edit to change protocol)
- `pins.json` (edit to change pin assignments)
- Documentation

### CI Verification (Recommended)

```bash
# Verify generated files are up-to-date
make generate
git diff --exit-code host/mara_host/config/
git diff --exit-code firmware/mcu/include/config/
```

---

## Feature Flag Architecture (MCU)

The MCU firmware uses compile-time feature flags for binary size optimization.

### Pattern

Each subsystem uses conditional compilation:

```cpp
#if HAS_FEATURE
    // Full implementation
    class MyManager { ... };
#else
    // Stub implementation (no-op, preserves API)
    class MyManager {
        void init() {}
        void loop() {}
    };
#endif
```

### Available Flags

| Flag | Default | Description |
|------|---------|-------------|
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
|---------|----------|------------|
| `esp32_minimal` | UART only | ~350KB |
| `esp32_motors` | Motors + encoders | ~550KB |
| `esp32_control` | Full control system | ~750KB |
| `esp32_full` | Everything | ~870KB |

---

## Testing Strategy

### Unit Tests

| Layer | Framework | Command |
|-------|-----------|---------|
| Host Python | pytest | `make test-host` |
| MCU C++ | PlatformIO Unity | `make test-mcu` |

### Integration Tests

| Test Type | Location | Description |
|-----------|----------|-------------|
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

## Architectural Decisions

### ADR-001: Monorepo Structure

**Decision**: Combine host, MCU firmware, and CAM firmware in one repo.

**Rationale**:
- Protocol changes are atomic (single commit updates both sides)
- Shared schema prevents version drift
- Unified testing and CI
- Simpler developer onboarding

**Trade-offs**:
- Larger clone size
- Must coordinate releases across components

### ADR-002: Code Generation for Protocol

**Decision**: Generate command/telemetry code from `platform_schema.py`.

**Rationale**:
- Single source of truth prevents mismatch
- Guarantees host and firmware use same definitions
- Enables schema evolution tracking

**Trade-offs**:
- Adds build step
- Generated code can be harder to debug

### ADR-003: Feature Flags for MCU

**Decision**: Use compile-time `#if HAS_*` flags with stub implementations.

**Rationale**:
- Minimizes flash usage for resource-constrained deployments
- Stubs preserve API for compile-time checking
- Clearer than complex template metaprogramming

**Trade-offs**:
- Some code duplication (full + stub blocks)
- Must maintain both implementations

### ADR-004: Camera as Separate Firmware

**Decision**: Keep CAM firmware independent of MCU firmware.

**Rationale**:
- Different hardware (ESP32-CAM vs ESP32)
- Camera concerns don't belong in control loop
- Allows independent deployment/updates

**Trade-offs**:
- Two firmware targets to maintain
- No direct MCU↔CAM communication

---

## Glossary

| Term | Definition |
|------|------------|
| **Host** | The Python runtime on developer's machine |
| **MCU** | The ESP32 motor controller target |
| **CAM** | The ESP32-CAM vision target |
| **Transport** | Communication layer (Serial, TCP, CAN, MQTT, BLE) |
| **Frame** | A protocol message with header, payload, and CRC |
| **Handler** | MCU-side command processor |
| **Module** | Lifecycle-managed subsystem (both host and MCU) |
| **SignalBus** | Real-time value routing system on MCU |
| **ControlKernel** | State-space controller execution engine |

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

*This document is the canonical system architecture reference. Update it when making architectural changes.*
