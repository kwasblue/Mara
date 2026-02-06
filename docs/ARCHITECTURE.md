# MARA Host Architecture

**Modular Asynchronous Robotics Architecture - Python Host Component**

---

## Overview

The MARA Host library (`robot_host`) follows a layered, async-first architecture for controlling ESP32-based robots. This is the Python component of the MARA framework.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Application                            │
│                  (examples, custom code)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   AsyncRobotClient                       │    │
│  │        (main interface, lifecycle, state machine)        │    │
│  └───────────────────────────┬─────────────────────────────┘    │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────┐      │
│  │                       EventBus                         │      │
│  │              (publish/subscribe messaging)             │      │
│  └─────────────────────────┬─────────────────────────────┘      │
│                            │                                     │
│  ┌──────────┬──────────┬───┴───┬──────────┬──────────┬─────────┐│
│  │ Command  │Telemetry │Module │ Control  │ Research │Recording││
│  │  Layer   │  Layer   │ Layer │  Design  │  Tools   │  Tools  ││
│  ├──────────┼──────────┼───────┼──────────┼──────────┼─────────┤│
│  │ Reliable │ Parser   │Motion │StateSpace│Simulation│Recording││
│  │Commander │ Models   │GPIO   │ LQR/PP   │ SysID    │ Replay  ││
│  │Connection│HostMod  │Encoder│ Observer │ Metrics  │ Analysis││
│  │ Monitor  │FileLog  │ IMU   │ Upload   │ Plotting │         ││
│  └──────────┴──────────┴───────┴──────────┴──────────┴─────────┘│
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────┐      │
│  │                    Transport Layer                     │      │
│  ├─────────────┬─────────────┬─────────────┬─────────────┤      │
│  │   Serial    │    TCP      │  Bluetooth  │   Stream    │      │
│  │  Transport  │  Transport  │  Transport  │  Transport  │      │
│  └─────────────┴─────────────┴─────────────┴─────────────┘      │
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────┐      │
│  │                    Protocol Layer                      │      │
│  │               (frame encoding/decoding)                │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### AsyncRobotClient

Main interface for robot communication:

```python
class AsyncRobotClient:
    def __init__(self, transport, bus=None, ...):
        self.transport = transport
        self.bus = bus or EventBus()
        self.connection = ConnectionMonitor(...)
        self.commander = ReliableCommander(...)

    async def start(self):
        # 1. Start transport
        # 2. Perform version handshake
        # 3. Start heartbeat loop
        # 4. Start connection monitor

    async def stop(self):
        # 1. Cancel heartbeat
        # 2. Stop monitors
        # 3. Close transport
```

### EventBus

Decoupled pub/sub messaging:

```python
class EventBus:
    def subscribe(self, topic: str, handler: Callable):
        self._handlers[topic].append(handler)

    def publish(self, topic: str, data: Any):
        for handler in self._handlers.get(topic, []):
            handler(data)
```

Common topics:
- `telemetry.*` - Sensor data
- `cmd.*` - Command ACKs
- `connection.*` - Connection events
- `heartbeat` - Keep-alive

### ReliableCommander

Guaranteed delivery with retries:

```python
class ReliableCommander:
    async def send(self, cmd_type, payload, wait_for_ack=True):
        seq = await self.send_func(cmd_type, payload)
        if wait_for_ack:
            future = self._pending[seq].future
            return await future  # (ok, error)
        return True, None

    def on_ack(self, seq, ok, error):
        cmd = self._pending.pop(seq)
        cmd.future.set_result((ok, error))
```

### Transport Layer

Abstract interface for communication:

```python
class HasSendBytes(Protocol):
    async def send_bytes(self, data: bytes) -> None: ...
    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None: ...
    def start(self) -> object: ...
    def stop(self) -> object: ...
```

Implementations:
- `SerialTransport` - USB/UART serial
- `AsyncTcpTransport` - WiFi TCP with auto-reconnect
- `BluetoothTransport` - Bluetooth Classic

## Message Flow

### Command with ACK

```
AsyncRobotClient                ReliableCommander              Transport
      │                                │                            │
      │ send_reliable("CMD_ARM", {})   │                            │
      ├───────────────────────────────►│                            │
      │                                │   send_bytes(frame)        │
      │                                ├───────────────────────────►│
      │                                │                            │
      │                                │   (pending[seq] = Future)  │
      │                                │                            │
      │                                │◄────── ACK frame ──────────│
      │                                │                            │
      │                                │   on_ack(seq, ok, error)   │
      │                                │   future.set_result(...)   │
      │                                │                            │
      │◄───────────── (ok, error) ─────┤                            │
      │                                │                            │
```

### Telemetry Flow

```
Transport              EventBus              TelemetryHostModule
    │                      │                         │
    │ frame received       │                         │
    ├─────────────────────►│                         │
    │ publish("telemetry.raw", data)                 │
    │                      ├────────────────────────►│
    │                      │                         │ parse(data)
    │                      │                         │
    │                      │◄────────────────────────┤
    │                      │ publish("telemetry.imu", imu)
    │                      │                         │
    │                      │◄────────────────────────┤
    │                      │ publish("telemetry.encoder0", enc)
    │                      │                         │
```

## Protocol

### Frame Format

```
┌────────┬────────┬────────┬──────────┬─────────────┬──────────────┐
│ HEADER │ LEN_HI │ LEN_LO │ MSG_TYPE │   PAYLOAD   │  CRC16       │
│  0xAA  │   1B   │   1B   │    1B    │   N bytes   │   2B         │
└────────┴────────┴────────┴──────────┴─────────────┴──────────────┘

CRC16-CCITT (polynomial 0x1021, initial 0xFFFF) calculated over:
LEN_HI + LEN_LO + MSG_TYPE + PAYLOAD
```

### Optimized Parsing

```python
_HEADER_BYTE = bytes([HEADER])

def extract_frames(buffer, on_frame):
    i = 0
    n = len(buffer)

    while i + MIN_FRAME_HEADER <= n:
        # Vectorized header search (faster than byte-by-byte)
        if buffer[i] != HEADER:
            idx = buffer.find(_HEADER_BYTE, i)
            if idx == -1:
                break
            i = idx

        # Parse frame...
```

## Control Design Module

Scipy-based tools for designing state-space controllers and observers.

### Components

```
robot_host/control/
├── state_space.py   # StateSpaceModel class, discretization
├── design.py        # LQR, pole placement, observer gains
├── upload.py        # MCU upload helpers
└── examples.py      # Usage examples
```

### Design Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Control Design Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐      ┌─────────────────┐               │
│  │  StateSpaceModel │─────►│   lqr() / PP    │               │
│  │  (A, B, C, D)    │      │  (gain design)  │               │
│  └─────────────────┘      └────────┬────────┘               │
│                                    │                         │
│                                    ▼                         │
│                           ┌─────────────────┐               │
│                           │  check_stability │               │
│                           │  (validation)    │               │
│                           └────────┬────────┘               │
│                                    │                         │
│                                    ▼                         │
│  ┌─────────────────┐      ┌─────────────────┐               │
│  │   observer_gains │─────►│ configure_state │               │
│  │   (L matrix)     │      │  _feedback()    │               │
│  └─────────────────┘      └────────┬────────┘               │
│                                    │                         │
│                                    ▼                         │
│                           ┌─────────────────┐               │
│                           │  MCU Upload     │               │
│                           │ (K, Kr, Ki, L)  │               │
│                           └─────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Example Usage

```python
from robot_host.control import (
    StateSpaceModel, lqr, observer_gains, configure_state_feedback
)
import numpy as np

# Define system
A = np.array([[0, 1], [-10, -0.5]])
B = np.array([[0], [1]])
C = np.array([[1, 0]])
model = StateSpaceModel(A, B, C)

# Design LQR controller
K, S, E = lqr(A, B, Q=np.diag([100, 1]), R=np.array([[1]]))

# Design observer
L = observer_gains(A, C, poles=[-25, -30])

# Upload to MCU
result = await configure_state_feedback(
    client, model, K,
    L=L,
    use_observer=True,
    signals={"state": [10, 11], "control": [20], "measurement": [30]},
)
```

---

## Research Module

### Simulation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SimulationRunner                          │
│              (coordinates simulation loop)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐      ┌─────────────────┐               │
│  │  DiffDriveRobot │◄────►│   Controller    │               │
│  │   (physics)     │      │  (user-defined) │               │
│  └────────┬────────┘      └─────────────────┘               │
│           │                                                  │
│  ┌────────┴────────┐                                        │
│  │                 │                                        │
│  ▼                 ▼                                        │
│ ┌─────────┐  ┌──────────┐  ┌────────────┐                   │
│ │ DCMotor │  │ DCMotor  │  │ NoiseModels│                   │
│ │  Left   │  │  Right   │  │(IMU,Enc,US)│                   │
│ └─────────┘  └──────────┘  └────────────┘                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Config Loading

```yaml
# robot_config.yaml
name: my_robot
type: diff_drive

drive:
  wheel_radius: 0.05
  wheel_base: 0.2

noise:
  imu:
    accel_std: 0.01
    gyro_std: 0.001
```

```python
robot = load_robot("robot_config.yaml")
```

## Optimization Techniques

### Lazy Dict Copying

```python
# Before: Copy on every update (150 objects/sec at 50Hz)
spec.latest_payload = dict(payload)

# After: Store reference, copy only when consumed
spec.latest_payload = payload
spec._payload_dirty = True

def _get_payload(spec):
    if spec._payload_dirty:
        result = dict(spec.latest_payload)
        spec._payload_dirty = False
        return result
    return spec.latest_payload
```

### Bounded Pending Commands

```python
MAX_PENDING_AGE_S = 30.0

async def _update(self):
    for seq, cmd in list(self._pending.items()):
        age = (now - cmd.first_sent_ns) / 1e9
        if age > MAX_PENDING_AGE_S:
            # Force evict stale commands (memory leak prevention)
            self._pending.pop(seq)
            cmd.future.set_result((False, "STALE"))
```

## Extending the Library

### Adding a New Module

```python
# robot_host/my_module/manager.py
from robot_host.command.client import AsyncRobotClient
from robot_host.core.event_bus import EventBus

class MyModuleHostModule:
    def __init__(self, bus: EventBus, client: AsyncRobotClient):
        self._bus = bus
        self._client = client
        bus.subscribe("telemetry.my_sensor", self._on_data)

    async def send_command(self, param: float):
        await self._client.cmd_my_command(param=param)

    def _on_data(self, data):
        # Process incoming data
        self._bus.publish("my_module.processed", processed_data)
```

### Adding a New Transport

```python
class MyTransport:
    def __init__(self, ...):
        self._frame_handler = lambda x: None

    def set_frame_handler(self, handler):
        self._frame_handler = handler

    async def start(self):
        # Initialize connection
        pass

    async def stop(self):
        # Close connection
        pass

    async def send_bytes(self, data: bytes):
        # Send data
        pass

    def _on_receive(self, data: bytes):
        # Called when data received
        extract_frames(self._buffer, self._frame_handler)
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=robot_host

# Run specific test
pytest tests/test_protocol.py -v
```

Test structure:
```
tests/
├── test_protocol.py      # Frame encoding/decoding
├── test_event_bus.py     # Pub/sub system
├── test_client.py        # AsyncRobotClient
├── test_commander.py     # ReliableCommander
└── test_hil/             # Hardware-in-loop tests
```
