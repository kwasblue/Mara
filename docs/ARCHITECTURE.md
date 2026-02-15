# MARA Host Architecture

**Modular Asynchronous Robotics Architecture - Python Host Component**

---

## Overview

The MARA Host library (`robot_host`) is a **platform** providing composable building blocks for controlling ESP32-based robots. The design prioritizes flexibility and extensibility over opinionated abstractions.

## Host vs MCU Control Model

The MARA system supports two control architectures:

### Option A: Host Streaming (Teleoperation/Research)

```
┌─────────────────┐      50Hz       ┌─────────────────┐
│  Python Host    │ ──SET_VEL────►  │      MCU        │
│  (controller)   │                 │  (motor driver) │
└─────────────────┘                 └─────────────────┘
```

Use when:
- Teleoperation (joystick control)
- Research/prototyping (iterate in Python)
- ML controllers (neural net on host)

```python
# Host streams velocity commands at 50Hz
async def teleop_loop(client, joystick):
    while True:
        vx = joystick.get_axis(1) * MAX_VEL
        omega = joystick.get_axis(0) * MAX_OMEGA
        await client.send_vel_binary(vx, omega)
        await asyncio.sleep(0.02)  # 50Hz
```

### Option B: MCU Control (Autonomous/Low-Latency)

```
┌─────────────────┐    on change    ┌─────────────────┐
│  Python Host    │ ──SET_SIGNAL──► │      MCU        │
│  (supervisor)   │                 │ (FreeRTOS ctrl) │
└─────────────────┘                 └─────────────────┘
```

Use when:
- Autonomous navigation
- Low-latency requirements
- Disconnection tolerance needed

```python
# Host sets references, MCU runs 100Hz control loop
async def nav_loop(client, path_planner):
    # Configure MCU controller once
    await client.send_json("CMD_CTRL_SLOT_CONFIG", {...})
    await client.send_json("CMD_CTRL_SLOT_ENABLE", {"slot": 0, "enable": True})

    while not at_goal:
        target_vel = path_planner.compute_velocity()
        await client.send_signal_binary(SIG_VX_REF, target_vel)
        await asyncio.sleep(0.1)  # 10Hz is fine - MCU handles timing
```

### Key Methods

| Method | Use Case | Protocol |
|--------|----------|----------|
| `send_vel_binary(vx, omega)` | Host streaming | Binary, 9 bytes |
| `send_signal_binary(id, val)` | MCU control | Binary, 7 bytes |
| `send_json(cmd, payload)` | Configuration | JSON, ~50 bytes |
| `send_reliable(cmd, payload)` | Config with ACK | JSON + retry |

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Application                            │
│                  (examples, custom robots)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                        Robot                             │    │
│  │     (main entry point, exposes HostModules as props)     │    │
│  │  ┌────────┬────────┬─────────┬─────────┬─────────┐      │    │
│  │  │ .gpio  │ .pwm   │ .motion │ .client │  .bus   │      │    │
│  │  └────────┴────────┴─────────┴─────────┴─────────┘      │    │
│  └───────────────────────────┬─────────────────────────────┘    │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────┐      │
│  │                    HostModules                         │      │
│  │     (hw/, motor/, sensor/, module/ - building blocks)  │      │
│  ├──────────┬──────────┬──────────┬──────────┬───────────┤      │
│  │ GpioHost │ PwmHost  │ Motion   │ Encoder  │ Telemetry │      │
│  │ Module   │ Module   │ HostMod  │ HostMod  │ HostMod   │      │
│  ├──────────┴──────────┴──────────┴──────────┴───────────┤      │
│  │              CameraHostModule (module/camera/)         │      │
│  │      ESP32-CAM streaming, presets, ML preprocessing    │      │
│  └───────────────────────────────────────────────────────┘      │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────┐      │
│  │              AsyncRobotClient + EventBus               │      │
│  │         (command handling, pub/sub messaging)          │      │
│  └─────────────────────────┬─────────────────────────────┘      │
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

## Design Philosophy

The library is a **platform**, not a product:

- **Building blocks** - HostModules are composable primitives
- **Direct access** - Robot exposes HostModules as lazy properties
- **No lock-in** - Import HostModules directly for custom setups
- **Extensible** - Easy to add new modules following the pattern

## Core Components

### Robot

Main entry point exposing HostModules as lazy properties:

```python
from robot_host import Robot

async with Robot("/dev/ttyUSB0") as robot:
    # HostModules via properties
    await robot.gpio.write(0, 1)
    await robot.pwm.set(0, duty=0.5)
    await robot.motion.set_velocity(0.3, 0.0)

    # Direct client access for advanced use
    await robot.client.cmd_some_command(param=1)

    # EventBus for pub/sub
    robot.on("telemetry.imu", handler)
```

### HostModules

Building blocks that wrap client commands. Each takes `(bus, client)`:

```python
from robot_host.hw.gpio import GpioHostModule
from robot_host.motor.motion import MotionHostModule

# Use directly with your own infrastructure
gpio = GpioHostModule(my_bus, my_client)
await gpio.write(channel=0, value=1)
```

### CameraHostModule

Standalone module for ESP32-CAM integration (doesn't require AsyncRobotClient):

```python
from robot_host.core.event_bus import EventBus
from robot_host.module.camera import CameraHostModule

bus = EventBus()
camera = CameraHostModule(bus, cameras={0: "http://10.0.0.66"})

# Subscribe to frames
bus.subscribe("camera.frame.0", on_frame)
bus.subscribe("camera.ml_frame.0", on_ml_frame)

# Control via commands
bus.publish("cmd.camera", {
    "cmd": "CMD_CAM_START_CAPTURE",
    "camera_id": 0,
    "mode": "streaming",
})
```

Features:
- MJPEG streaming (~15 FPS) via port 81
- ML preprocessing (224x224, ImageNet normalized, CHW format)
- 9 presets (streaming, night, ml_inference, surveillance, etc.)
- Multi-camera support
- Recording to video/images

See `robot_host/module/camera/README.md` for full documentation.

### AsyncRobotClient

Low-level interface for robot communication:

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
- `cmd.camera` - Camera commands
- `camera.frame.<id>` - Camera frames (BGR)
- `camera.ml_frame.<id>` - ML-ready frames (224x224, CHW)
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
