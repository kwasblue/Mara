# MARA Host Examples

Educational examples demonstrating MARA (Modular Asynchronous Robotics Architecture) usage patterns.

## Directory Structure

```
examples/
├── connections/          # Basic transport examples
│   ├── serial_basic.py   # Serial port connection
│   ├── tcp_basic.py      # TCP/WiFi connection
│   └── can_basic.py      # CAN bus connection
│
├── shells/               # Interactive shell implementations
│   ├── interactive_shell.py
│   ├── serial_shell.py
│   ├── bluetooth_shell.py
│   └── telemetry_shell.py
│
├── motors/               # Motor control examples
│   ├── pid_test.py       # Basic PID testing
│   ├── pid_sweep.py      # PID parameter sweep
│   └── stepper_test.py   # Stepper motor testing
│
├── streaming/            # Data streaming
│   └── stream_basic.py   # Basic streaming example
│
├── recording/            # Session recording
│   ├── record_session.py # Record a session
│   └── replay_metrics.py # Replay and analyze
│
└── applications/         # Complete applications
    ├── pill_carousel.py  # Pill dispenser control
    ├── pill_gui.py       # Pill dispenser GUI
    ├── camera_basic.py   # Basic camera capture
    ├── camera_host.py    # Camera host module
    ├── camera_detection.py # Object detection
    ├── detection.py      # General detection
    └── mqtt_nodes.py     # MQTT node management
```

## Running Examples

Most examples can be run directly:

```bash
# From repository root
python -m mara_host.examples.connections.serial_basic

# Or with Python path
cd mara_host/examples
python connections/serial_basic.py
```

## Common Patterns

### 1. Basic Connection

```python
from mara_host.command.factory import create_client_from_args
# OR
from mara_host.command.client import MaraClient
from mara_host.transport.serial_transport import SerialTransport

async def main():
    transport = SerialTransport("/dev/cu.usbserial-0001", baudrate=115200)
    client = MaraClient(transport)

    await client.start()
    try:
        await client.cmd_arm()
        # ... do work ...
    finally:
        await client.cmd_disarm()
        await client.stop()
```

### 2. Event Handling

```python
client.bus.subscribe("telemetry", handle_telemetry)
client.bus.subscribe("heartbeat", handle_heartbeat)
```

### 3. Reliable Commands

```python
ok, error = await client.send_reliable("CMD_ARM", {})
if not ok:
    print(f"Command failed: {error}")
```
