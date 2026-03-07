# MQTT Multi-Node Guide

**Control multiple ESP32 nodes over MQTT**

---

## Overview

MARA supports controlling multiple ESP32 nodes over MQTT, enabling fleet-wide robot coordination. This guide covers the MQTT transport layer, multi-node discovery, and coordination patterns.

## Architecture

```
┌────────────────────────────────────┐
│               HOST                 │
│  (Linux / Mac / SBC / PC)          │
│                                    │
│  ┌──────────────┐   ┌────────────┐ │
│  │ NodeManager  │   │ Video Mux  │ │
│  │  + Router    │   │ Recorder   │ │
│  └──────┬───────┘   └─────┬──────┘ │
│         │ Control Plane   │        │
│         │ (MQTT)          │        │
│    ┌────▼─────┐           │        │
│    │  MQTT    │           │        │
│    │  Broker  │           │        │
│    └────┬─────┘           │        │
└─────────┼─────────────────┼────────┘
          │                 │
     Wi-Fi / Ethernet LAN   │
          │                 │
    ┌─────┴─────┐     ┌─────┴─────┐
    │           │     │           │
┌───▼───────┐ ┌─▼─────────┐ ┌─────▼─────┐
│  NODE 0   │ │  NODE 1   │ │  NODE N   │
│  (ESP32)  │ │  (ESP32)  │ │  (ESP32)  │
│           │ │           │ │           │
│ Control   │ │ Control   │ │ Control   │
│ App       │ │ App       │ │ App       │
│    │      │ │    │      │ │    │      │
│ MQTT      │ │ MQTT      │ │ MQTT      │
│ Transport │ │ Transport │ │ Transport │
│    │      │ │    │      │ │    │      │
│ Motors/   │ │ Motors/   │ │ Motors/   │
│ Sensors   │ │ Sensors   │ │ Sensors   │
└───────────┘ └───────────┘ └───────────┘
```

## MQTT Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `mara/fleet/discover` | Host → All | Discovery request |
| `mara/fleet/discover_response` | Node → Host | Discovery response with node info |
| `mara/{node_id}/cmd` | Host → Node | Commands (binary framed) |
| `mara/{node_id}/ack` | Node → Host | Command acknowledgments |
| `mara/{node_id}/telemetry` | Node → Host | Telemetry data |
| `mara/{node_id}/state` | Node → Host | Node state changes |

## Quick Start

### 1. Start MQTT Broker

The easiest way is using the MARA CLI:

```bash
# Start broker (runs in background, listens on all interfaces)
mara mqtt start

# Check status
mara mqtt status

# Stop broker
mara mqtt stop
```

Or manually with mosquitto:

```bash
# Install mosquitto (if not installed)
brew install mosquitto  # macOS
sudo apt install mosquitto  # Linux

# Start broker
mosquitto -c /path/to/mosquitto.conf -v
```

Minimal `mosquitto.conf`:
```
listener 1883 0.0.0.0
allow_anonymous true
```

### 2. Discover and Control Nodes

```python
import asyncio
from mara_host.core.event_bus import EventBus
from mara_host.transport.mqtt import NodeManager

async def main():
    bus = EventBus()
    manager = NodeManager(
        bus=bus,
        broker_host="10.0.0.59",  # Your broker IP
        broker_port=1883,
    )

    await manager.start()

    # Discover all nodes on the network
    nodes = await manager.discover(timeout_s=5.0)
    print(f"Found {len(nodes)} node(s)")

    for info in nodes:
        print(f"  {info.node_id}: {info.board} (fw={info.firmware})")

    # Get a specific node
    node0 = manager.get_node("node0")
    if node0 and node0.is_online:
        # Send commands
        await node0.client.arm()
        await node0.client.set_vel(vx=0.2, omega=0.0)
        await asyncio.sleep(2.0)
        await node0.client.cmd_stop()
        await node0.client.disarm()

    # Broadcast to all nodes
    results = await manager.broadcast_stop()
    for node_id, (ok, err) in results.items():
        print(f"  {node_id}: {'OK' if ok else err}")

    await manager.stop()

asyncio.run(main())
```

### 3. Run the Example Script

```bash
python -m mara_host.examples.applications.mqtt_nodes --broker 10.0.0.59
```

## NodeManager API

### Initialization

```python
from mara_host.transport.mqtt import NodeManager

manager = NodeManager(
    bus=EventBus(),
    broker_host="10.0.0.59",
    broker_port=1883,
    fallback_broker=None,      # Optional fallback broker
    username=None,             # MQTT auth (optional)
    password=None,
    heartbeat_timeout_s=5.0,   # Node offline detection
    require_version_match=True, # Enforce protocol version
)
```

### Discovery

```python
# Discover all nodes (blocks for timeout_s)
nodes = await manager.discover(timeout_s=5.0)

# Each NodeInfo contains:
# - node_id: str
# - firmware: str
# - protocol: int
# - board: str
# - state: NodeState
# - features: List[str]
```

### Node Access

```python
# Get specific node
node = manager.get_node("node0")

# Get all nodes
all_nodes = manager.get_nodes()

# Get online/offline lists
online = manager.get_online_nodes()   # ["node0", "node1"]
offline = manager.get_offline_nodes() # ["node2"]
```

### Broadcasting

```python
# Send command to all online nodes
results = await manager.broadcast("CMD_ARM")

# Convenience methods
await manager.broadcast_stop()   # CMD_STOP to all
await manager.broadcast_estop()  # CMD_ESTOP to all
```

### Events

```python
bus.subscribe("node.discovered", lambda d: print(f"New: {d['node_id']}"))
bus.subscribe("node.online.node0", lambda d: print("node0 online"))
bus.subscribe("node.offline.node0", lambda d: print("node0 offline"))
bus.subscribe("node.added", lambda d: print(f"Added: {d['node_id']}"))
bus.subscribe("node.removed", lambda d: print(f"Removed: {d['node_id']}"))
```

## NodeProxy API

Each discovered node gets a `NodeProxy` wrapper:

```python
node = manager.get_node("node0")

# Check status
node.is_online          # bool
node.node_id            # "node0"
node.info               # NodeInfo from discovery
node.status             # NodeStatus (last_seen, latency, etc.)

# Access the underlying client
node.client.arm()
node.client.set_vel(vx=0.1, omega=0.0)
node.client.send_reliable("CMD_GPIO_WRITE", {"channel": 0, "value": 1})

# Send with automatic ACK handling
success, error = await node.send_reliable("CMD_ARM")
```

## Testing with Mock Nodes

You can simulate additional nodes without hardware:

```bash
# Terminal 1: Start mock node
python -m mara_host.tools.mock_node --node-id node1 --broker 10.0.0.59

# Terminal 2: Start another mock node
python -m mara_host.tools.mock_node --node-id node2 --broker 10.0.0.59

# Terminal 3: Run discovery
python -m mara_host.examples.applications.mqtt_nodes --broker 10.0.0.59
```

Mock node options:
```bash
python -m mara_host.tools.mock_node \
    --node-id node1 \
    --broker 10.0.0.59 \
    --port 1883 \
    --firmware "1.0.0-mock" \
    --board "mock-esp32"
```

## Protocol Details

### Frame Format

Commands are sent as binary frames (same as Serial/TCP):

```
┌────────┬────────┬────────┬──────────┬─────────────┬──────────────┐
│ HEADER │ LEN_HI │ LEN_LO │ MSG_TYPE │   PAYLOAD   │   CRC16      │
│  0xAA  │   1B   │   1B   │    1B    │   N bytes   │    2B        │
└────────┴────────┴────────┴──────────┴─────────────┴──────────────┘
```

### Discovery Protocol

1. Host publishes `{}` to `mara/fleet/discover`
2. Each node responds on `mara/fleet/discover_response`:

```json
{
  "node_id": "node0",
  "firmware": "1.0.0",
  "protocol": 1,
  "board": "esp32",
  "state": "online",
  "features": []
}
```

### Handshake

After discovery, each node performs a version handshake:

1. Host sends `MSG_VERSION_REQUEST` (0x04) to `mara/{node}/cmd`
2. Node responds with `MSG_VERSION_RESPONSE` (0x05) on `mara/{node}/ack`:

```json
{
  "firmware": "1.0.0",
  "protocol": 1,
  "board": "esp32",
  "name": "robot",
  "kind": "identity"
}
```

## Broker Failover

NodeManager supports automatic failover to a backup broker:

```python
manager = NodeManager(
    bus=bus,
    broker_host="192.168.1.100",     # Primary broker
    broker_port=1883,
    fallback_broker="192.168.1.1",   # Fallback (e.g., node0's built-in broker)
    fallback_port=1883,
)
```

When the primary broker becomes unreachable, NodeManager automatically reconnects all nodes to the fallback broker.

## ESP32 Firmware Setup

### 1. Enable MQTT in Build

Use a WiFi-enabled build profile:

```bash
# Build with full features (WiFi + MQTT)
cd firmware/mcu && pio run -e esp32_usb
```

Or enable in `platformio.ini`:
```ini
build_flags =
    -DHAS_WIFI=1
    -DHAS_MQTT_TRANSPORT=1
```

### 2. Configure WiFi and Broker

Edit `firmware/mcu/include/config/WifiSecrets.h`:

```cpp
// WiFi credentials
#define WIFI_STA_SSID        "YourNetworkName"
#define WIFI_STA_PASSWORD    "YourPassword"

// MQTT broker (your host machine's IP)
#define MQTT_BROKER_HOST     "10.0.0.59"
#define MQTT_BROKER_PORT     1883
#define MQTT_ROBOT_ID        "mara_bot"
```

### 3. Flash Firmware

```bash
cd firmware/mcu && pio run -e esp32_usb -t upload
```

## Troubleshooting

### No nodes discovered

1. Check broker is running: `mosquitto_sub -h localhost -t '#' -v`
2. Verify ESP32 is connected to WiFi
3. Check ESP32 serial output for MQTT connection status
4. Ensure firewall allows port 1883

### Handshake timeout

1. Check ESP32 is subscribed to `mara/{node_id}/cmd`
2. Verify frame parsing with `Protocol::extractFrames()`
3. Check CRC calculation matches between host and firmware

### Commands not acknowledged

1. Ensure ACK format includes `seq`, `src`, `ok` fields:
```json
{"type": "ACK", "cmd": "CMD_STOP", "seq": 1, "src": "mcu", "ok": true}
```

### Connection spam

If you see repeated connect/disconnect messages:
1. Check for duplicate client IDs
2. Verify broker allows multiple connections
3. Ensure discovery stops after initial scan (default behavior)

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall system architecture
- [ADDING_COMMANDS.md](ADDING_COMMANDS.md) - Adding new commands
- [README.md](../README.md) - Quick start guide
