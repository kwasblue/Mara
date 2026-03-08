# MARA Host Architecture

<div align="center">

**Modular Asynchronous Robotics Architecture**

*Python Host Component*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Overview

MARA Host (`mara_host`) is a **platform** providing composable building blocks for controlling ESP32-based robots. The design prioritizes clarity, performance, and extensibility.

---

## System Diagram

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           USER APPLICATION                                 ┃
┃                      (scripts, notebooks, CLI)                            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                                            ┃
┃  ╔═══════════════════════════════════════════════════════════════════╗    ┃
┃  ║                         Robot                                      ║    ┃
┃  ║              (main entry point, context manager)                   ║    ┃
┃  ║  ┌─────────┬─────────┬──────────┬──────────┬─────────┬─────────┐  ║    ┃
┃  ║  │  .gpio  │  .pwm   │ .motion  │  .servo  │ .client │  .bus   │  ║    ┃
┃  ║  └─────────┴─────────┴──────────┴──────────┴─────────┴─────────┘  ║    ┃
┃  ╚═══════════════════════════════════════════════════════════════════╝    ┃
┃                                   │                                        ┃
┃  ╔════════════════════════════════╧════════════════════════════════╗      ┃
┃  ║                    API Layer  (api/)                             ║      ┃
┃  ║      User-facing interfaces with validation & exceptions        ║      ┃
┃  ║  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       ║      ┃
┃  ║  │   GPIO   │   PWM    │  Servo   │  Motor   │ Encoder  │       ║      ┃
┃  ║  └──────────┴──────────┴──────────┴──────────┴──────────┘       ║      ┃
┃  ╚════════════════════════════════╤════════════════════════════════╝      ┃
┃                                   │                                        ┃
┃  ╔════════════════════════════════╧════════════════════════════════╗      ┃
┃  ║                  Service Layer  (services/)                      ║      ┃
┃  ║       State tracking, limits, validation, returns ServiceResult  ║      ┃
┃  ║  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       ║      ┃
┃  ║  │  GPIO    │  Motion  │  Servo   │  Motor   │  State   │       ║      ┃
┃  ║  │ Service  │ Service  │ Service  │ Service  │ Service  │       ║      ┃
┃  ║  └──────────┴──────────┴──────────┴──────────┴──────────┘       ║      ┃
┃  ╚════════════════════════════════╤════════════════════════════════╝      ┃
┃                                   │                                        ┃
┃  ╔════════════════════════════════╧════════════════════════════════╗      ┃
┃  ║                      MaraClient  (command/)                      ║      ┃
┃  ║           Coordinator: routing, handshake, telemetry             ║      ┃
┃  ╠══════════════════════════════════════════════════════════════════╣      ┃
┃  ║  ┌────────────────────────────────────────────────────────────┐  ║      ┃
┃  ║  │              ReliableCommander                              │  ║      ┃
┃  ║  │    ╭─────────────────────────────────────────────────────╮  │  ║      ┃
┃  ║  │    │  ALL commands flow through here (single chokepoint) │  │  ║      ┃
┃  ║  │    │                                                     │  │  ║      ┃
┃  ║  │    │  • Reliable: tracking, ACK, retries                 │  │  ║      ┃
┃  ║  │    │  • Streaming: fire-and-forget (binary=True/False)   │  │  ║      ┃
┃  ║  │    │  • Event emission for debugging                     │  │  ║      ┃
┃  ║  │    ╰─────────────────────────────────────────────────────╯  │  ║      ┃
┃  ║  └────────────────────────────────────────────────────────────┘  ║      ┃
┃  ╚════════════════════════════════╤════════════════════════════════╝      ┃
┃                                   │                                        ┃
┃  ╔════════════════════════════════╧════════════════════════════════╗      ┃
┃  ║                    Protocol  (core/protocol.py)                  ║      ┃
┃  ║           Frame encoding, CRC16-CCITT, binary/JSON               ║      ┃
┃  ╚════════════════════════════════╤════════════════════════════════╝      ┃
┃                                   │                                        ┃
┃  ╔════════════════════════════════╧════════════════════════════════╗      ┃
┃  ║                  Transport Layer  (transport/)                   ║      ┃
┃  ║  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       ║      ┃
┃  ║  │  Serial  │   TCP    │Bluetooth │   MQTT   │   CAN    │       ║      ┃
┃  ║  └──────────┴──────────┴──────────┴──────────┴──────────┘       ║      ┃
┃  ╚════════════════════════════════╤════════════════════════════════╝      ┃
┃                                   │                                        ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                    │
                              ══════╧══════
                                   MCU
                              ESP32 Firmware
```

---

## Command Flow

All commands flow through **ReliableCommander** - the single chokepoint for debugging and event logging.

### Two Paths, One Entry Point

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│    robot.motion.set_velocity(0.5, 0.0, binary=True)                    │
│                            │                                            │
│                            ▼                                            │
│    ┌─────────────────────────────────────────────────────────────────┐ │
│    │  MotionService.set_velocity()                                    │ │
│    │  • Apply limits/clamping                                        │ │
│    │  • Track last_velocity state                                    │ │
│    └───────────────────────────┬─────────────────────────────────────┘ │
│                                │                                        │
│                                ▼                                        │
│    ┌─────────────────────────────────────────────────────────────────┐ │
│    │  MaraClient.send_stream(binary=True)                            │ │
│    └───────────────────────────┬─────────────────────────────────────┘ │
│                                │                                        │
│                                ▼                                        │
│    ╔═════════════════════════════════════════════════════════════════╗ │
│    ║          ReliableCommander.send_fire_and_forget()               ║ │
│    ║                                                                  ║ │
│    ║   binary=False              │              binary=True          ║ │
│    ║   ┌─────────────────┐       │       ┌─────────────────┐         ║ │
│    ║   │   JSON Path     │       │       │  Binary Path    │         ║ │
│    ║   │  ~50 bytes      │       │       │   9 bytes       │         ║ │
│    ║   └────────┬────────┘       │       └────────┬────────┘         ║ │
│    ║            │                │                │                   ║ │
│    ║            └────────────────┼────────────────┘                   ║ │
│    ║                             │                                    ║ │
│    ║              _emit("cmd.sent", ...)  ← Event for debugging      ║ │
│    ║              commands_sent += 1                                  ║ │
│    ╚═════════════════════════════╤═══════════════════════════════════╝ │
│                                  │                                      │
│                                  ▼                                      │
│    ┌─────────────────────────────────────────────────────────────────┐ │
│    │  Protocol.encode()  →  Transport.send_bytes()                   │ │
│    └─────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Command Methods

| Method | Path | Use Case |
|:-------|:-----|:---------|
| `send_reliable()` | Commander → track + ACK | Config, safety commands |
| `send_stream(binary=False)` | Commander → JSON fire-and-forget | Standard streaming |
| `send_stream(binary=True)` | Commander → binary fire-and-forget | High-rate (50+ Hz) |

---

## Layer Responsibilities

### API Layer (`api/`)

**Purpose:** User-facing interface with validation and clear exceptions.

```python
class GPIO:
    async def write(self, channel: int, value: int) -> None:
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} is not registered")
        result = await self._service.write(channel, value)
        if not result.ok:
            raise RuntimeError(result.error)
```

**Key principle:** API validates, Service executes, Client sends.

---

### Service Layer (`services/`)

**Purpose:** Business logic, state tracking, returns `ServiceResult`.

```python
class MotionService:
    async def set_velocity(self, vx: float, omega: float, binary: bool = True):
        # Apply limits
        vx = clamp(vx, -self._limit, self._limit)

        # Send through unified path
        await self.client.send_stream("CMD_SET_VEL", {"vx": vx, "omega": omega}, binary=binary)

        # Track state
        self._last_velocity = Velocity(vx, omega)
```

---

### MaraClient (`command/client.py`)

**Purpose:** Coordinator/facade that ties everything together.

**Responsibilities:**
- Transport lifecycle (start/stop)
- Version handshake
- Heartbeat loop
- Frame dispatch
- Routes to ReliableCommander

**Lazy initialization:** Logs are loaded on first access for faster startup.

---

### ReliableCommander

**Purpose:** Single chokepoint for all outgoing commands.

```python
class ReliableCommander:
    async def send_fire_and_forget(self, cmd_type: str, payload: dict, binary: bool = False):
        """All streaming commands flow through here."""
        if binary and self.send_binary_func:
            await self.send_binary_func(cmd_type, payload)
        else:
            await self.send_func(cmd_type, payload, None)

        self.commands_sent += 1
        self._emit("cmd.sent", ...)  # For debugging
```

**Stats available:**
- `commands_sent`
- `commands_sent_binary`
- `acks_received`
- `timeouts`
- `retries`

---

### Transport Layer

**Optimizations in `StreamTransport`:**

```python
class StreamTransport:
    def __init__(self):
        # asyncio.Lock for async coordination (no thread overhead)
        self._async_lock = asyncio.Lock()

        # Dedicated executor (single thread, reused)
        self._write_executor = ThreadPoolExecutor(max_workers=1)

        # Cached loop reference
        self._cached_loop = None

    async def send_bytes(self, data: bytes):
        async with self._async_lock:  # Serialize async callers
            await self._cached_loop.run_in_executor(
                self._write_executor,
                self._send_bytes_sync,
                data
            )
```

---

## EventBus

Simple pub/sub with async support.

```python
class EventBus:
    def publish(self, topic: str, data: Any) -> None:
        """Synchronous dispatch (fast)."""

    async def publish_async(self, topic: str, data: Any) -> None:
        """Async dispatch - awaits async handlers."""
```

**Common topics:**

| Topic | Description |
|:------|:------------|
| `telemetry` | All telemetry packets |
| `telemetry.imu` | IMU data |
| `telemetry.encoder0` | Encoder data |
| `cmd.sent` | Command sent events |
| `connection.lost` | Disconnection |
| `connection.restored` | Reconnection |

---

## Protocol

### Frame Format

```
┌────────┬────────┬────────┬──────────┬─────────────┬──────────────┐
│ HEADER │ LEN_HI │ LEN_LO │ MSG_TYPE │   PAYLOAD   │    CRC16     │
│  0xAA  │   1B   │   1B   │    1B    │   N bytes   │     2B       │
└────────┴────────┴────────┴──────────┴─────────────┴──────────────┘
```

**CRC16-CCITT** (polynomial 0x1021, initial 0xFFFF) over: `LEN_HI + LEN_LO + MSG_TYPE + PAYLOAD`

### Message Types

| Type | ID | Description |
|:-----|:---|:------------|
| `MSG_HEARTBEAT` | 0x01 | Keep-alive |
| `MSG_PING` | 0x02 | Ping request |
| `MSG_PONG` | 0x03 | Ping response |
| `MSG_VERSION_REQUEST` | 0x04 | Request firmware info |
| `MSG_VERSION_RESPONSE` | 0x05 | Firmware info response |
| `MSG_TELEMETRY_BIN` | 0x30 | Binary telemetry |
| `MSG_CMD_JSON` | 0x50 | JSON command |
| `MSG_CMD_BIN` | 0x51 | Binary command |

### Wire Size Comparison

| Encoding | SET_VEL Payload | Total Frame |
|:---------|:----------------|:------------|
| JSON | ~50 bytes | ~56 bytes |
| Binary | 9 bytes | ~15 bytes |

---

## Performance Optimizations

### Startup Time

| Optimization | Impact |
|:-------------|:-------|
| Lazy yaml import | 50-100ms saved |
| Lazy MaraLogBundle | 50-100ms saved |
| Lazy HostModule creation | Resources on-demand |

### Runtime

| Optimization | Impact |
|:-------------|:-------|
| Binary encoding | 73% wire size reduction |
| asyncio.Lock | No thread spawn overhead |
| Cached executor | Thread reuse |
| Cached event loop | Avoid lookup per call |

---

## Example Usage

### Basic Control

```python
from mara_host import Robot

async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
    await robot.activate()

    # High-rate velocity streaming (50+ Hz)
    for _ in range(100):
        await robot.motion.set_velocity(0.3, 0.0, binary=True)
        await asyncio.sleep(0.02)

    await robot.deactivate()
    await robot.disarm()
```

### Telemetry

```python
async with Robot("/dev/ttyUSB0") as robot:
    @robot.on("telemetry.imu")
    def on_imu(data):
        print(f"Accel: {data['ax']:.2f}, {data['ay']:.2f}")

    await robot.arm()
    await asyncio.sleep(10)
    await robot.disarm()
```

---

## File Structure

```
mara_host/
├── robot.py                    # Robot facade
├── api/                        # User-facing API
│   ├── gpio.py
│   ├── servo.py
│   └── ...
├── services/                   # Business logic
│   └── control/
│       ├── gpio_service.py
│       ├── motion_service.py
│       └── ...
├── command/                    # Protocol handling
│   ├── client.py              # MaraClient
│   ├── coms/
│   │   ├── reliable_commander.py
│   │   └── connection_monitor.py
│   └── binary_mixin.py
├── core/                       # Infrastructure
│   ├── protocol.py
│   ├── event_bus.py
│   └── settings.py
├── transport/                  # Physical layer
│   ├── serial_transport.py
│   ├── tcp_transport.py
│   ├── stream_transport.py
│   └── mqtt/
└── telemetry/                  # Sensor data
    ├── binary_parser.py
    └── models.py
```

---

## Related Documentation

| Document | Description |
|:---------|:------------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | Quick start guide |
| [ADDING_COMMANDS.md](ADDING_COMMANDS.md) | Adding new commands |
| [EXTENDING.md](EXTENDING.md) | Adding sensors, motors, transports |
| [MQTT.md](MQTT.md) | Multi-node control |
| [CODEGEN.md](CODEGEN.md) | Code generation system |

---

<div align="center">

*MARA Host v1.0*

</div>
