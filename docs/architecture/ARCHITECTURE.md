# MARA Architecture

<div align="center">

**Modular Asynchronous Robotics Architecture**

*Complete system architecture for ESP32-based robotics*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER APPLICATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Public API (api/)                                                           │
│  ├── GPIO, PWM, Servo, DCMotor, Encoder                                     │
│  └── Validates inputs → routes to Services → raises exceptions              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Services Layer (services/control/)                                          │
│  ├── GpioService, MotionService, ServoService, MotorService, StateService   │
│  └── Business logic → state tracking → returns ServiceResult                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Client Layer (command/client.py)                                            │
│  ├── MaraClient: coordinator, handshake, routing                            │
│  └── Routes to ReliableCommander (single chokepoint)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Commander Layer (command/coms/reliable_commander.py)                        │
│  ├── ALL commands flow here (reliable & streaming)                          │
│  ├── Reliable: ACK tracking, retries, sequence numbers                      │
│  └── Streaming: fire-and-forget, optional binary (binary=True)              │
├─────────────────────────────────────────────────────────────────────────────┤
│  EventBus (core/)                                                            │
│  └── Pub/sub for telemetry, connection, debugging events                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Protocol (core/protocol.py)                                                 │
│  └── Frame encoding, CRC16, message types                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Transport Layer (transport/)                                                │
│  ├── SerialTransport (USB)     │  AsyncTcpTransport (WiFi)                  │
│  └── CANTransport (CAN bus)    │  MqttTransport (Fleet)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ESP32 MCU Firmware (C++)
```

---

## Layer Responsibilities

### API Layer (`api/`)

User-facing interface that validates inputs and raises exceptions.

```python
class GPIO:
    async def write(self, channel: int, value: int) -> None:
        """Write a digital value to a channel."""
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")

        result = await self._service.write(channel, value)

        if not result.ok:
            raise RuntimeError(result.error)
```

| Does | Does NOT |
|:-----|:---------|
| Validate user inputs | Implement business logic |
| Raise exceptions | Format wire protocol |
| Route to services | Manage state |

---

### Services Layer (`services/control/`)

Business logic that tracks state and returns `ServiceResult`.

```python
class GpioService:
    async def write(self, channel: int, value: int) -> ServiceResult:
        """Write a digital value to a GPIO channel."""
        value = 1 if value else 0

        ok, error = await self.client.send_reliable(
            "CMD_GPIO_WRITE",
            {"channel": channel, "value": value},
        )

        if ok:
            self._channels[channel].value = value
            return ServiceResult.success(data={"channel": channel, "value": value})
        else:
            return ServiceResult.failure(error=error or "Failed")
```

| Does | Does NOT |
|:-----|:---------|
| Business logic | Raise exceptions |
| State tracking | Parse arguments |
| Call client methods | Format for display |

---

### Client Layer (`command/client.py`)

Coordinator that routes commands to the commander.

```python
class MaraClient:
    async def send_stream(
        self,
        cmd_type: str,
        payload: dict,
        request_ack: bool = False,
        binary: bool = False,
    ):
        """Send a command (streaming or reliable)."""
        if request_ack:
            return await self.send_reliable(cmd_type, payload)

        # ALL commands flow through commander
        await self.commander.send_fire_and_forget(cmd_type, payload, binary=binary)
        return True, None
```

| Does | Does NOT |
|:-----|:---------|
| Route commands | Know about specific hardware |
| Manage connection | Implement business logic |
| Coordinate subsystems | Track domain state |

---

### Commander Layer (`command/coms/reliable_commander.py`)

**Single chokepoint** for ALL commands—enables debugging and metrics.

```python
class ReliableCommander:
    async def send_fire_and_forget(
        self,
        cmd_type: str,
        payload: dict,
        binary: bool = False,
    ) -> None:
        """Fire-and-forget send (streaming path)."""
        sent_ns = time.monotonic_ns()

        if binary and self.send_binary_func:
            await self.send_binary_func(cmd_type, payload)
            self.commands_sent_binary += 1
        else:
            await self.send_func(cmd_type, payload, None)

        self.commands_sent += 1
        self._emit("cmd.sent", cmd_type=cmd_type, binary=binary, sent_ns=sent_ns)
```

| Path | Use Case | Wire Size |
|:-----|:---------|:----------|
| `send()` (reliable) | Setup, config, critical commands | ~50 bytes (JSON) |
| `send_fire_and_forget(binary=False)` | General streaming | ~50 bytes (JSON) |
| `send_fire_and_forget(binary=True)` | High-rate control (50+ Hz) | ~9 bytes (binary) |

---

### Transport Layer (`transport/`)

Raw byte I/O with async coordination.

```python
class StreamTransport:
    async def send_bytes(self, data: bytes) -> None:
        """Send bytes with asyncio coordination."""
        loop = self._cached_loop or asyncio.get_running_loop()
        async with self._async_lock:
            await loop.run_in_executor(self._write_executor, self._send_bytes_sync, data)
```

| Does | Does NOT |
|:-----|:---------|
| Raw byte I/O | Parse commands |
| Connection lifecycle | Know about JSON/binary |
| Frame buffering | Business logic |

---

## Command Flow

### Standard Command (GPIO Write)

```
User: await gpio.write(0, 1)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  API Layer: gpio.write()                                    │
│  • Validate: is_registered(0)? ✓                           │
│  • Call: self._service.write(0, 1)                         │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer: GpioService.write()                         │
│  • Normalize: value = 1                                     │
│  • Call: client.send_reliable("CMD_GPIO_WRITE", {...})     │
│  • Track: ch.value = 1                                      │
│  • Return: ServiceResult.success()                          │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Commander: ReliableCommander.send()                        │
│  • Encode: JSON                                             │
│  • Track: seq=42, pending[42]=Future                       │
│  • Emit: "cmd.sent" event                                  │
│  • Send: transport.send_bytes(frame)                       │
│  • Wait: await future (for ACK)                            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   Transport → MCU → ACK → Resolve Future
```

### High-Rate Streaming (50+ Hz)

```
User: await motion.set_velocity(0.5, 0.0, binary=True)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer: MotionService.set_velocity()                │
│  • Clamp: vx = clamp(0.5, -1.0, 1.0)                       │
│  • Call: client.send_stream(..., binary=True)              │
│  • Track: _last_velocity = Velocity(0.5, 0.0)              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Commander: send_fire_and_forget(binary=True)               │
│  • Encode: struct.pack("<Bff", OPCODE, 0.5, 0.0)           │
│  • Emit: "cmd.sent" event (for debugging)                  │
│  • Stats: commands_sent_binary += 1                        │
│  • Send: transport.send_bytes(frame)                       │
│  • No wait (fire-and-forget)                               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   9 bytes payload → ~15 bytes on wire (vs ~50 bytes JSON)
```

---

## Telemetry Flow

```
MSG_TELEMETRY_BIN payload
    ↓
parse_telemetry_bin(bytes)
    ├── Header: version, seq, ts_ms, section_count
    └── Sections: section_id, length, data
    ↓
TelemetryPacket (dataclass)
    ├── imu: ImuTelemetry
    ├── encoder0: EncoderTelemetry
    └── ... (optional fields)
    ↓
EventBus.publish("telemetry", packet)
EventBus.publish("telemetry.imu", imu_data)
```

**Telemetry sections** (`TELEM_*` constants):

| ID | Section | Data |
|:---|:--------|:-----|
| `0x00` | IMU | Accelerometer, gyroscope |
| `0x01` | Ultrasonic | Distance readings |
| `0x03` | Encoder0 | Position, velocity |
| `0x04` | Stepper0 | Position, state |
| `0x10` | Control Signals | Signal bus snapshot |
| `0x11` | Control Observers | Observer state |

---

## Package Responsibilities

| Package | Responsibility |
|:--------|:---------------|
| `robot.py` | Main entry point; lazy transport/client setup |
| `api/` | Public user-facing classes with validation |
| `services/control/` | Business logic and state tracking |
| `command/` | Client coordination and reliable delivery |
| `core/` | EventBus, protocol encoding, module interfaces |
| `transport/` | Physical layer implementations |
| `telemetry/` | Binary parsing and telemetry models |
| `config/` | Configuration loading + generated code |
| `tools/` | Code generators |
| `cli/` | Command-line interface |

---

## Key Design Patterns

### 1. Single Chokepoint

All commands flow through `ReliableCommander`, enabling:
- Unified event emission for debugging
- Consistent metrics collection
- Single place to add logging/tracing

### 2. ServiceResult Pattern

Services return results instead of raising exceptions:

```python
@dataclass
class ServiceResult:
    ok: bool
    data: Optional[dict] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, data=None) -> "ServiceResult":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, error: str) -> "ServiceResult":
        return cls(ok=False, error=error)
```

### 3. Lazy Initialization

Robot doesn't create transport/client until `connect()`. Services created on first access.

### 4. Binary Optimization

High-rate commands use binary encoding:
- JSON: ~50 bytes, good for setup/config
- Binary: ~9 bytes, 5x smaller, use for streaming

---

## Frame Protocol

All transports use the same frame format:

```
┌────────┬────────┬────────┬──────────┬─────────────┬──────────────┐
│ HEADER │ LEN_HI │ LEN_LO │ MSG_TYPE │   PAYLOAD   │   CRC16      │
│  0xAA  │   1B   │   1B   │    1B    │   N bytes   │    2B        │
└────────┴────────┴────────┴──────────┴─────────────┴──────────────┘
```

**Message types** (`core/protocol.py`):

| Type | ID | Description |
|:-----|:---|:------------|
| `MSG_HEARTBEAT` | `0x01` | Keep-alive |
| `MSG_PING` | `0x02` | Latency check |
| `MSG_PONG` | `0x03` | Ping response |
| `MSG_VERSION_REQUEST` | `0x04` | Request firmware info |
| `MSG_VERSION_RESPONSE` | `0x05` | Firmware info response |
| `MSG_TELEMETRY_BIN` | `0x30` | Binary telemetry |
| `MSG_CMD_JSON` | `0x50` | JSON command |
| `MSG_CMD_BIN` | `0x51` | Binary command |

---

## Generated vs Hand-Written Code

### Generated Files (DO NOT EDIT)

| Generator | Output | Purpose |
|:----------|:-------|:--------|
| `gen_commands.py` | `config/client_commands.py` | `cmd_*()` methods |
| `gen_commands.py` | `config/command_defs.py` | `CommandDef` dataclasses |
| `gen_binary_commands.py` | `command/json_to_binary.py` | Binary encoding |
| `gen_telemetry.py` | `telemetry/telemetry_sections.py` | Section IDs |

**Regenerate after editing schema:**
```bash
mara generate all
```

### Source of Truth

`tools/schema/` package defines all commands, payloads, and directions.

---

## File Reference

```
mara_host/
├── robot.py                    # Robot facade
├── api/                        # Public API (validation, exceptions)
│   ├── gpio.py
│   ├── servo.py
│   └── dc_motor.py
├── services/control/           # Business logic (ServiceResult)
│   ├── gpio_service.py
│   ├── motion_service.py
│   └── state_service.py
├── command/
│   ├── client.py               # MaraClient (coordinator)
│   └── coms/
│       ├── reliable_commander.py  # Single chokepoint
│       └── connection_monitor.py
├── core/
│   ├── event_bus.py            # Pub/sub
│   ├── protocol.py             # Frame encoding
│   └── result.py               # ServiceResult
├── transport/
│   ├── serial_transport.py
│   ├── tcp_transport.py
│   └── stream_transport.py     # Base with asyncio.Lock
├── telemetry/
│   ├── binary_parser.py
│   └── models.py
├── config/                     # Generated code
└── tools/                      # Generators
```

---

<div align="center">

*This is the canonical architecture reference. Update it when making architectural changes.*

</div>
