# MARA Architecture

> Modular Asynchronous Robotics Architecture

This document describes the architecture of the mara_host Python package and its relationship with the ESP32 MCU firmware.

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER APPLICATION                      │
├─────────────────────────────────────────────────────────┤
│  Public API (api/)                                       │
│  ├─ GPIO, PWM, Encoder, IMU, Stepper, Servo, DCMotor    │
│  └─ DifferentialDrive, VelocityController               │
├─────────────────────────────────────────────────────────┤
│  Runtime + BaseModule                                    │
│  └─ Lifecycle management, event subscriptions, ticking  │
├─────────────────────────────────────────────────────────┤
│  Robot + HostModules (hw/, motor/, sensor/)             │
│  └─ CommandHostModule, EventHostModule                  │
├─────────────────────────────────────────────────────────┤
│  AsyncRobotClient (command/)                            │
│  ├─ ReliableCommander (retries/acking)                  │
│  ├─ ConnectionMonitor (health)                          │
│  └─ RobotCommandsMixin (generated cmd_* methods)        │
├─────────────────────────────────────────────────────────┤
│  EventBus (core/)                                        │
│  └─ Pub/sub for telemetry, connection, events           │
├─────────────────────────────────────────────────────────┤
│  Telemetry (telemetry/)                                 │
│  └─ binary_parser: raw bytes → TelemetryPacket          │
├─────────────────────────────────────────────────────────┤
│  Protocol (core/protocol.py)                            │
│  └─ Frame encoding, CRC16, message types                │
├─────────────────────────────────────────────────────────┤
│  Transport Layer (transport/)                           │
│  ├─ SerialTransport (USB)                               │
│  ├─ AsyncTcpTransport (WiFi)                            │
│  └─ CANTransport (CAN bus)                              │
└─────────────────────────────────────────────────────────┘
                         ↓
              ESP32 MCU Firmware (C++)
```

## Package Responsibilities

| Package | Responsibility |
|---------|----------------|
| `robot.py` | Main entry point; lazy transport/client setup |
| `core/` | EventBus, protocol encoding, module interfaces |
| `command/` | AsyncRobotClient, reliable delivery, connection monitoring |
| `transport/` | Physical layer implementations (serial, TCP, CAN, BLE) |
| `telemetry/` | Binary parsing and telemetry models |
| `api/` | Public user-facing classes (Stepper, Servo, IMU, etc.) |
| `hw/` | GPIO/PWM HostModules |
| `motor/` | Motion control HostModules |
| `sensor/` | Sensor HostModules (IMU, Encoder) |
| `runtime/` | Execution loop and module lifecycle |
| `config/` | Configuration loading + generated code |
| `services/` | **Business logic layer** (extracted from CLI) |
| `tools/` | Code generators |
| `cli/` | Command-line interface (argument parsing, display) |
| `logger/` | Structured event logging (JSONL) |
| `research/` | Recording, replay, simulation, analysis |

### Services Layer

The `services/` package contains business logic extracted from CLI commands,
making it reusable from scripts, APIs, notebooks, and tests:

| Service | Purpose |
|---------|---------|
| `services/pins/` | GPIO pin management, conflict detection |
| `services/testing/` | Robot self-test suite |
| `services/transport/` | Connection and robot control (TODO) |
| `services/build/` | Firmware build orchestration (TODO) |
| `services/recording/` | Session recording and replay (TODO) |

### Generated Code

See [`mara_host/GENERATED_FILES.md`](mara_host/GENERATED_FILES.md) for the complete list of auto-generated files.

**Key principle**: Never edit generated files directly. Edit `tools/platform_schema.py` and run `mara generate all`.

## Composition Root

The **composition root** is the `Robot` class, which orchestrates creation of all dependencies:

```python
robot = Robot("/dev/ttyUSB0")  # Nothing created yet (lazy)

await robot.connect()
# Creates:
#   1. SerialTransport (or AsyncTcpTransport)
#   2. EventBus
#   3. AsyncRobotClient(transport, bus)
#   4. Performs version handshake

# HostModules created lazily on first access:
robot.gpio   # → GpioHostModule
robot.motion # → MotionHostModule
```

**Key principle**: `Robot` is the facade. `AsyncRobotClient` is the protocol engine. `Runtime` is the execution loop.

## Event Flow

### Incoming (MCU → Host)

```
Transport receives frame
    ↓
AsyncRobotClient._on_frame(body)
    ├─ MSG_TELEMETRY_BIN → parse_telemetry_bin() → TelemetryPacket
    ├─ MSG_CMD_JSON → parse JSON → extract topic
    └─ MSG_HEARTBEAT/PONG → connection.on_message_received()
    ↓
EventBus.publish(topic, data)
    ↓
├─ User callbacks: robot.on("telemetry.imu", handler)
├─ BaseModule.on_<topic>() methods (auto-wired)
├─ Sensor API subscriptions (IMU, Encoder cache data)
└─ HostModule transforms (ImuHostModule → ImuState)
```

### Outgoing (Host → MCU)

```
User: await robot.motion.set_velocity(0.5, 0.0)
    ↓
MotionHostModule.set_velocity()
    ↓
AsyncRobotClient.cmd_set_vel(vx, omega)  # generated method
    ↓
ReliableCommander.send_reliable()
    ├─ Track sequence number
    ├─ Encode to MSG_CMD_JSON or MSG_CMD_BIN
    └─ transport.send_bytes()
    ↓
Wait for ACK (future) or retry on timeout
```

## Transport Layer

All transports implement `AsyncBaseTransport`:

```python
class AsyncBaseTransport:
    def set_frame_handler(callback): ...  # Register incoming frame callback
    async def send_bytes(data): ...       # Send raw bytes
    def start(): ...                      # Open connection
    def stop(): ...                       # Close connection
```

**Frame format** (all transports):
```
[HEADER 0xAA][len_hi][len_lo][msg_type][payload...][crc_hi][crc_lo]
```

**Message types** (`core/protocol.py`):
```python
MSG_HEARTBEAT        = 0x01
MSG_PING             = 0x02
MSG_PONG             = 0x03
MSG_VERSION_REQUEST  = 0x04
MSG_VERSION_RESPONSE = 0x05
MSG_WHOAMI           = 0x10
MSG_TELEMETRY_BIN    = 0x30
MSG_CMD_JSON         = 0x50
MSG_CMD_BIN          = 0x51
```

## Telemetry Flow

```
MSG_TELEMETRY_BIN payload
    ↓
parse_telemetry_bin(bytes)
    ├─ Header: version, seq, ts_ms, section_count
    └─ Sections: section_id, length, data
    ↓
TelemetryPacket (dataclass)
    ├─ imu: ImuTelemetry
    ├─ encoder0: EncoderTelemetry
    ├─ stepper0: StepperTelemetry
    └─ ... (optional fields)
    ↓
EventBus.publish("telemetry", packet)
EventBus.publish("telemetry.imu", imu_data)
```

**Telemetry sections** (`TELEM_*` constants):
- `0x00` IMU
- `0x01` Ultrasonic
- `0x03` Encoder0
- `0x04` Stepper0
- `0x10` Control Signals
- `0x11` Control Observers

## Module Lifecycle

### BaseModule

```python
class MyModule(BaseModule):
    name = "my_module"

    def topics(self) -> list[str]:
        return ["telemetry.imu"]  # Auto-wire on_telemetry_imu()

    async def start(self) -> None: ...
    async def on_tick(self, dt: float) -> None: ...
    def on_telemetry_imu(self, data: dict) -> None: ...  # Auto-called
    async def stop(self) -> None: ...
```

### Runtime Execution

```python
runtime = Runtime(robot, tick_hz=50.0)
runtime.add_module(MyModule())

await runtime.run()
# 1. Attach modules
# 2. Start modules
# 3. Loop: call on_tick, dispatch events
# 4. Stop modules on exit
```

### MCU Module Registration (Firmware)

The ESP32 firmware has two module registration patterns:

**1. Self-Registration (Preferred)**

Uses `REGISTER_MODULE` macro for automatic registration:

```cpp
class StatusLedModule : public IModule {
public:
    StatusLedModule() = default;  // Requires default constructor

    void init(mcu::ServiceContext& ctx) override {
        bus_ = ctx.bus;  // Get dependencies from context
    }

    void loop(uint32_t now_ms) override { ... }
    const char* name() const override { return "StatusLed"; }

private:
    EventBus* bus_ = nullptr;
};

REGISTER_MODULE(StatusLedModule);  // Auto-registers before main()
```

**2. Manual Registration (Legacy)**

For modules with constructor dependencies:

```cpp
// In ServiceStorage.h
HeartbeatModule heartbeat{bus};  // Takes EventBus& in constructor

// In Runtime.cpp - must explicitly wire
if (ctx_.host && ctx_.heartbeat) {
    ctx_.host->addModule(ctx_.heartbeat);
}
```

**Important**: If a module is instantiated but not registered, its `loop()` will never be called. This was the cause of the HeartbeatModule bug.

## Generated vs Hand-Written Code

### Generated Files

All generators are in `tools/` and output to `config/` or `command/`:

| Generator | Output | Purpose |
|-----------|--------|---------|
| `gen_commands.py` | `config/client_commands.py` | `RobotCommandsMixin` with `cmd_*()` methods |
| `gen_commands.py` | `config/command_defs.py` | `CommandDef` dataclasses |
| `gen_binary_commands.py` | `command/json_to_binary.py` | High-rate binary encoding |
| `gen_telemetry.py` | `telemetry/telemetry_sections.py` | Section ID constants |
| `gen_version.py` | `config/version.py` | Protocol/schema versions |
| `gen_can.py` | `transport/can_defs_generated.py` | CAN message definitions |

**Run all generators:**
```bash
mara generate all
# or
python -m mara_host.tools.generate_all
```

### Source of Truth

`tools/platform_schema.py` defines all commands, their payloads, and directions. Generators read this schema.

### Pattern

```python
# Hand-written base class
class AsyncRobotClient(RobotCommandsMixin):
    async def send_reliable(self, cmd, payload, wait_for_ack=True): ...

# Generated mixin (don't edit!)
class RobotCommandsMixin:
    async def cmd_arm(self) -> None:
        await self.send_json_cmd('CMD_ARM', {})

    async def cmd_set_vel(self, vx: float, omega: float) -> None:
        await self.send_json_cmd('CMD_SET_VEL', {'vx': vx, 'omega': omega})
```

## Key Design Patterns

### 1. Lazy Initialization
Robot doesn't create transport/client until `connect()`. HostModules created on first property access.

### 2. Two-Tier API
- **Public API** (`api/`): User-friendly, state tracking, validation
- **HostModules** (`hw/`, `motor/`, `sensor/`): Thin wrappers around client

### 3. EventBus
Simple synchronous pub/sub. Topics use dot notation (`telemetry.imu`).

### 4. Reliable Commands
`ReliableCommander` tracks sequence numbers, implements retries, returns futures for acking.

### 5. Binary Optimization
High-rate commands (SET_VEL) can be encoded as 9-byte binary instead of ~50-byte JSON.

## Connection Management

### Handshake
```
1. Send MSG_VERSION_REQUEST
2. Receive MSG_VERSION_RESPONSE with firmware/protocol versions
3. Verify protocol version matches
4. Start heartbeat loop
5. Start connection monitor
```

### Health Monitoring
```python
ConnectionMonitor:
    - on_message_received() updates last_message_time
    - check() runs every 0.1s
    - If no message for 1.0s: publish "connection.lost"
    - On recovery: publish "connection.restored"
```

## CLI Architecture

Entry point: `mara_host/cli/main.py`

Commands are registered by modules in `cli/commands/`:
```
mara
├── run shell|serial|tcp|can
├── build compile|upload|clean
├── generate all|commands|pins|telemetry
├── pins pinout|list|free|assign
├── test all|connection|ping|motors
├── record <session>
├── config show|validate
└── logs view|tail
```

## File Reference

```
mara_host/
├── robot.py              # Robot facade
├── core/
│   ├── event_bus.py      # Pub/sub
│   ├── base_module.py    # Module interface
│   └── protocol.py       # Frame encoding
├── command/
│   ├── client.py         # AsyncRobotClient
│   └── coms/
│       ├── connection_monitor.py
│       └── reliable_commander.py
├── transport/
│   ├── serial_transport.py
│   ├── tcp_transport.py
│   └── can_transport.py
├── telemetry/
│   ├── binary_parser.py
│   └── models.py
├── api/                  # Public user API
├── hw/                   # GPIO/PWM modules
├── motor/                # Motion modules
├── sensor/               # Sensor modules
├── runtime/runtime.py    # Execution loop
├── config/               # Config + generated
├── tools/                # Generators
├── cli/                  # CLI commands
└── research/             # Recording/replay/analysis
```

## Architectural Decisions

### Why EventBus instead of direct callbacks?
- Decouples producers from consumers
- Easy to add logging/recording as subscribers
- Supports multiple listeners per topic

### Why generated command methods?
- 50+ commands would be tedious to maintain
- Schema is source of truth for both host and MCU
- Ensures consistency between Python and C++

### Why lazy initialization?
- Faster startup
- Resources allocated only when needed
- Easier testing (can inspect Robot without connecting)

### Why two-tier API?
- HostModules are internal, can change freely
- Public API is stable, user-facing contract
- Clear separation of concerns
