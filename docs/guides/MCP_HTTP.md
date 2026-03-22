# MCP & HTTP Server Guide

<div align="center">

**LLM-Ready Robot Control**

*Model Context Protocol for Claude + HTTP API for any LLM*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Overview

MARA provides two interfaces for LLM control:

| Interface | Protocol | Best For |
|:----------|:---------|:---------|
| **MCP Server** | Model Context Protocol | Claude Code, Claude Desktop |
| **HTTP Server** | REST API | OpenAI, local LLMs, any HTTP client |

Both interfaces share:
- Same `MaraRuntime` backend
- Same `StateStore` with freshness tracking
- Same command correlation and latency metrics
- Same tool definitions (generated from `tool_schema.py`)

---

## Quick Start

### MCP Mode (Claude Code)

```bash
# Add to Claude Code MCP settings
python -m mara_host.mcp
```

### HTTP Mode (Any LLM)

```bash
# Start HTTP server
mara mcp --http

# Or with custom port
mara mcp --http --http-port 8080
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         LLM Layer                           │
├─────────────┬─────────────────────────────────┬─────────────┤
│  Claude     │                                 │  OpenAI     │
│  (MCP)      │                                 │  (HTTP)     │
└──────┬──────┴─────────────────────────────────┴──────┬──────┘
       │                                               │
       ▼                                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      MaraRuntime                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    StateStore                        │   │
│  │  • FreshValue (fresh/aging/stale)                   │   │
│  │  • CommandRecords (seq_id, latency_ms)              │   │
│  │  • Events (connected, state_change, command_acked)  │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Services: servo_service, motor_service, gpio_service, ... │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  MaraClient → ReliableCommander → Transport → Hardware     │
└─────────────────────────────────────────────────────────────┘
```

---

## HTTP Endpoints

### State & Monitoring

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/state` | GET | Full robot state with freshness |
| `/freshness` | GET | Data staleness report |
| `/events?n=20` | GET | Recent events |
| `/commands?n=20` | GET | Command history + stats |
| `/schema` | GET | OpenAI-compatible function definitions |

### Connection

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/connect` | POST | Connect to robot |
| `/disconnect` | POST | Disconnect from robot |

### Actuators

| Endpoint | Method | Body |
|:---------|:-------|:-----|
| `/servo/attach` | POST | `{"servo_id": 0, "pin": 13}` |
| `/servo/set` | POST | `{"servo_id": 0, "angle": 90}` |
| `/servo/center` | POST | `{"servo_id": 0}` |
| `/motor/set` | POST | `{"motor_id": 0, "speed": 0.5}` |
| `/motor/stop` | POST | `{"motor_id": 0}` |
| `/gpio/write` | POST | `{"channel": 0, "value": 1}` |
| `/gpio/toggle` | POST | `{"channel": 0}` |
| `/stepper/move` | POST | `{"stepper_id": 0, "steps": 200}` |
| `/pwm/set` | POST | `{"channel": 0, "duty": 0.5}` |

### State Control

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/state/arm` | POST | Arm robot for operation |
| `/state/disarm` | POST | Disarm robot |
| `/state/stop` | POST | Emergency stop |

---

## MCP Tools

All tools are prefixed with `mara_`:

```
mara_connect          - Connect to robot
mara_disconnect       - Disconnect
mara_get_state        - Get full state
mara_get_freshness    - Get data freshness
mara_get_events       - Get recent events
mara_get_command_stats - Get command statistics

mara_arm              - Arm robot
mara_disarm           - Disarm robot
mara_stop             - Emergency stop

mara_servo_attach     - Attach servo to pin
mara_servo_set        - Move servo to angle
mara_servo_center     - Center servo
mara_servo_detach     - Detach servo

mara_motor_set        - Set motor speed
mara_motor_stop       - Stop motor

mara_gpio_write       - Set GPIO high/low
mara_gpio_toggle      - Toggle GPIO
mara_gpio_read        - Read GPIO state

mara_stepper_move     - Move stepper by steps
mara_stepper_stop     - Stop stepper

mara_pwm_set          - Set PWM duty cycle

mara_encoder_read     - Read encoder
mara_encoder_reset    - Reset encoder

mara_imu_read         - Read IMU data
```

---

## State & Freshness

### State Snapshot

```json
{
  "connected": true,
  "robot_state": {
    "value": "ARMED",
    "age_s": 0.5,
    "freshness": "fresh"
  },
  "firmware": "0.5.0",
  "features": ["servo", "motor", "gpio", "imu"],
  "imu": {
    "value": {"ax": 0.01, "ay": 0.02, "az": 9.8, ...},
    "age_s": 0.1,
    "freshness": "fresh"
  },
  "command_stats": {
    "total": 42,
    "successful": 41,
    "failed": 1,
    "success_rate": 0.976,
    "avg_latency_ms": 45.3,
    "pending": 0
  },
  "recent_commands": [...],
  "recent_events": [...]
}
```

### Freshness Levels

| Level | Meaning | Threshold |
|:------|:--------|:----------|
| `fresh` | Recently updated | < 50% of stale threshold |
| `aging` | Getting old | 50-100% of stale threshold |
| `stale` | Needs refresh | > stale threshold |

Default thresholds:
- Robot state: 2.0s
- IMU/Encoders: 0.5s

---

## Command Tracking

Every command is tracked with:

```json
{
  "seq_id": 42,
  "command": "servo_set",
  "params": {"servo_id": 0, "angle": 90},
  "sent_at": "2024-01-15T10:30:00.123",
  "acked_at": "2024-01-15T10:30:00.168",
  "success": true,
  "error": null,
  "latency_ms": 45.2
}
```

---

## Events

Events are recorded for:

| Event Type | When |
|:-----------|:-----|
| `connected` | Robot connection established |
| `disconnected` | Robot disconnected |
| `state_change` | Robot state changed (IDLE→ARMED, etc.) |
| `command_acked` | Command succeeded |
| `command_failed` | Command failed |

Example event:
```json
{
  "type": "command_acked",
  "timestamp": "2024-01-15T10:30:00.168",
  "data": {
    "seq_id": 42,
    "command": "servo_set",
    "success": true,
    "latency_ms": 45.2
  }
}
```

---

## Adding New Tools

### 1. Edit `mcp/tool_schema.py`

```python
ToolDef(
    name="my_action",
    description="Description for LLM.",
    category="mydevice",
    service="my_service",
    method="do_action",
    params=(
        ToolParam("device_id", "integer", "Device ID"),
        ToolParam("value", "number", "Value to set"),
        ToolParam("optional_param", "integer", "Optional", required=False, default=0),
    ),
    requires_arm=True,  # Call ensure_armed() before execution
    response_format="Device {device_id} set to {value}",
),
```

### 2. Run generator

```bash
mara generate all
# or just MCP:
mara generate mcp
```

### 3. Done!

- MCP: `mara_my_action` tool
- HTTP: `POST /mydevice/action` endpoint

---

## Tool Schema Reference

### ToolDef Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | str | Tool name (becomes `mara_<name>` for MCP) |
| `description` | str | Description shown to LLM |
| `category` | str | Grouping (servo, motor, gpio, etc.) |
| `service` | str | Service property on runtime |
| `method` | str | Method to call on service |
| `params` | tuple | Parameter definitions |
| `requires_arm` | bool | Call `ensure_armed()` before execution |
| `client_method` | str | Direct client method (instead of service) |
| `response_format` | str | f-string template for success response |
| `custom_handler` | bool | Use custom handler function |

### ToolParam Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | str | Parameter name |
| `type` | str | JSON Schema type: integer, number, string, boolean |
| `description` | str | Description for LLM |
| `required` | bool | Whether parameter is required |
| `default` | any | Default value if not provided |
| `service_name` | str | Map to different name for service call |

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| `MARA_PORT` | Serial port | From config |
| `MARA_HOST` | TCP host | None |
| `MARA_TCP_PORT` | TCP port | 3333 |

### Command Line

```bash
# Serial connection
mara mcp --http -p /dev/ttyUSB0

# TCP connection
mara mcp --http --tcp 192.168.4.1 --tcp-port 3333

# Custom HTTP port
mara mcp --http --http-port 8080
```

---

## OpenAI Integration

Get function definitions for OpenAI:

```bash
curl http://localhost:8000/schema
```

Response:
```json
{
  "functions": [
    {
      "name": "mara_servo_set",
      "description": "Move a servo to the specified angle.",
      "parameters": {
        "type": "object",
        "properties": {
          "servo_id": {"type": "integer", "description": "Servo ID (0-7)"},
          "angle": {"type": "number", "description": "Angle in degrees (0-180)"}
        },
        "required": ["servo_id", "angle"]
      }
    },
    ...
  ]
}
```

---

## Example: Python Client

```python
import httpx

async def control_robot():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Check state
        state = (await client.get("/state")).json()
        print(f"Connected: {state['connected']}")
        print(f"Robot state: {state['robot_state']['value']}")

        # Move servo
        await client.post("/servo/attach", json={"servo_id": 0, "pin": 13})
        await client.post("/servo/set", json={"servo_id": 0, "angle": 90})

        # Check command stats
        stats = (await client.get("/commands")).json()["stats"]
        print(f"Avg latency: {stats['avg_latency_ms']:.1f}ms")
```

---

<div align="center">

*One tool definition, two interfaces (MCP + HTTP)*

</div>
