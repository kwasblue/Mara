# Extending MARA

This guide covers how to extend the MARA platform with new transports, sensors, motors, and host modules.

**Prerequisites:** Read [ADDING_COMMANDS.md](./ADDING_COMMANDS.md) first for command/protocol extension.

---

## Table of Contents

1. [Adding a New Transport](#adding-a-new-transport)
2. [Adding a New Sensor](#adding-a-new-sensor)
3. [Adding a New Motor Type](#adding-a-new-motor-type)
4. [Adding a Host Module](#adding-a-host-module)
5. [Adding a Service](#adding-a-service)

---

## Adding a New Transport

Transports handle communication between the Python host and ESP32 MCU.

### Existing Transports

| Transport | File | Use Case |
|-----------|------|----------|
| Serial | `serial_transport.py` | USB connection |
| TCP | `tcp_transport.py` | WiFi connection |
| CAN | `can_transport.py` | CAN bus |
| Bluetooth | `bluetooth_transport.py` | Bluetooth Classic |

### Step 1: Create Transport Class

Extend `AsyncBaseTransport` and implement the required methods:

```python
# transport/websocket_transport.py

import asyncio
from typing import Optional
from mara_host.core import protocol
from mara_host.transport.async_base_transport import AsyncBaseTransport

class WebSocketTransport(AsyncBaseTransport):
    """
    WebSocket transport for browser-based control.
    """

    def __init__(self, url: str, reconnect_delay: float = 5.0) -> None:
        super().__init__()
        self.url = url
        self.reconnect_delay = reconnect_delay
        self._ws = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._rx_buffer = bytearray()

    @property
    def is_connected(self) -> bool:
        return self._ws is not None

    async def start(self) -> None:
        """Start connection loop in background."""
        if self._task is None:
            self._running = True
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop connection and cleanup."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send_bytes(self, data: bytes) -> None:
        """Send raw bytes over WebSocket."""
        if not self._ws:
            print("[WebSocketTransport] send_bytes called while not connected")
            return
        await self._ws.send(data)

    async def _run(self) -> None:
        """Main connection/read loop."""
        import websockets

        while self._running:
            try:
                print(f"[WebSocketTransport] Connecting to {self.url}...")
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    print("[WebSocketTransport] Connected")
                    self._rx_buffer.clear()

                    async for message in ws:
                        if isinstance(message, bytes):
                            self._rx_buffer.extend(message)
                            # Parse frames using MARA protocol
                            protocol.extract_frames(self._rx_buffer, self._handle_frame)

            except Exception as e:
                print(f"[WebSocketTransport] Error: {e}")
                self._ws = None

            if self._running:
                print(f"[WebSocketTransport] Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
```

### Step 2: Register in `__init__.py`

```python
# transport/__init__.py

from .websocket_transport import WebSocketTransport

__all__ = [
    # ... existing exports
    "WebSocketTransport",
]
```

### Step 3: Add Factory Support (Optional)

Update the client factory to support the new transport:

```python
# command/factory.py

def create_websocket_client(self, url: str, config: Optional[ClientConfig] = None):
    from mara_host.transport.websocket_transport import WebSocketTransport
    transport = WebSocketTransport(url)
    return self._create_client(transport, config)
```

### Step 4: Add CLI Support (Optional)

Add a new run subcommand:

```python
# cli/commands/run/websocket.py

async def cmd_websocket(args: argparse.Namespace) -> int:
    from mara_host.transport.websocket_transport import WebSocketTransport
    transport = WebSocketTransport(args.url)
    # ... standard connection flow
```

---

## Adding a New Sensor

Adding a sensor requires changes on both MCU (C++) and Host (Python) sides.

### Existing Sensors

| Sensor | MCU Manager | Host Module |
|--------|-------------|-------------|
| Encoder | `EncoderManager` | `EncoderHostModule` |
| IMU | `ImuManager` | `ImuHostModule` |
| Ultrasonic | `UltrasonicManager` | `UltrasonicHostModule` |

### Step 1: Define Commands in Schema

Edit `host/mara_host/tools/platform_schema.py`:

```python
# In COMMANDS dict
"CMD_LIDAR_ATTACH": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "Attach a LiDAR sensor.",
    "payload": {
        "sensor_id": {"type": "int", "required": True},
        "rx_pin": {"type": "int", "required": True},
        "tx_pin": {"type": "int", "required": True},
    },
},
"CMD_LIDAR_READ": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "Read LiDAR distance.",
    "payload": {
        "sensor_id": {"type": "int", "required": True},
    },
},
```

### Step 2: Add Telemetry Section (If Streaming)

For high-rate sensor data, add a telemetry section:

```python
# In TELEMETRY_SECTIONS dict
"TELEM_LIDAR": {
    "id": 0x08,  # Next available ID
    "description": "LiDAR distance data",
    "format": "sensor_id(u8) distance_mm(u16) quality(u8) ts_ms(u32)",
    "size": 8,
},
```

### Step 3: Generate Code

```bash
mara generate all
```

### Step 4: Create MCU Sensor Manager

```cpp
// firmware/mcu/include/sensor/LidarManager.h

#pragma once
#include <cstdint>

class LidarManager {
public:
    static constexpr int MAX_SENSORS = 2;

    bool attach(uint8_t id, uint8_t rxPin, uint8_t txPin);
    int16_t readDistanceMm(uint8_t id);
    uint8_t getQuality(uint8_t id);

private:
    struct Sensor {
        bool attached = false;
        uint8_t rxPin = 0;
        uint8_t txPin = 0;
    };
    Sensor sensors_[MAX_SENSORS];
};
```

### Step 5: Add Handler Methods

Add to `SensorHandler.h` or create a new `LidarHandler.h`:

```cpp
// In SensorHandler.h or new LidarHandler.h

bool canHandle(CmdType cmd) const override {
    switch (cmd) {
        // ... existing cases
        case CmdType::LIDAR_ATTACH:
        case CmdType::LIDAR_READ:
            return true;
        default:
            return false;
    }
}

void handleLidarAttach(JsonVariantConst payload, CommandContext& ctx) {
    int sensorId = payload["sensor_id"] | 0;
    int rxPin = payload["rx_pin"] | 0;
    int txPin = payload["tx_pin"] | 0;

    bool ok = lidar_.attach(sensorId, rxPin, txPin);

    JsonDocument resp;
    resp["sensor_id"] = sensorId;
    ctx.sendAck("CMD_LIDAR_ATTACH", ok, resp);
}

void handleLidarRead(JsonVariantConst payload, CommandContext& ctx) {
    int sensorId = payload["sensor_id"] | 0;

    int16_t distMm = lidar_.readDistanceMm(sensorId);
    uint8_t quality = lidar_.getQuality(sensorId);

    JsonDocument resp;
    resp["sensor_id"] = sensorId;
    resp["distance_mm"] = distMm;
    resp["quality"] = quality;
    ctx.sendAck("CMD_LIDAR_READ", true, resp);
}
```

### Step 6: Create Host Module

```python
# host/mara_host/sensor/lidar.py

from dataclasses import dataclass
from mara_host.command.client import MaraClient
from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import CommandHostModule


@dataclass
class LidarDefaults:
    sensor_id: int = 0
    rx_pin: int = 16
    tx_pin: int = 17


class LidarHostModule(CommandHostModule):
    """
    Host-side wrapper for LiDAR sensor commands.
    """

    module_name = "lidar"

    def __init__(
        self,
        bus: EventBus,
        client: MaraClient,
        defaults: LidarDefaults | None = None,
    ) -> None:
        super().__init__(bus, client)
        self._defaults = defaults or LidarDefaults()

    async def attach(
        self,
        sensor_id: int | None = None,
        rx_pin: int | None = None,
        tx_pin: int | None = None,
    ) -> None:
        sid = sensor_id if sensor_id is not None else self._defaults.sensor_id
        rx = rx_pin if rx_pin is not None else self._defaults.rx_pin
        tx = tx_pin if tx_pin is not None else self._defaults.tx_pin

        await self._client.cmd_lidar_attach(
            sensor_id=sid,
            rx_pin=rx,
            tx_pin=tx,
        )

    async def read(self, sensor_id: int | None = None) -> dict:
        sid = sensor_id if sensor_id is not None else self._defaults.sensor_id
        return await self._client.cmd_lidar_read(sensor_id=sid)
```

### Step 7: Export Module

```python
# host/mara_host/sensor/__init__.py

from .lidar import LidarHostModule, LidarDefaults

__all__ = [
    # ... existing exports
    "LidarHostModule",
    "LidarDefaults",
]
```

---

## Adding a New Motor Type

Similar to sensors, motors require MCU driver + host module.

### Existing Motors

| Motor | MCU Manager | Host Module |
|-------|-------------|-------------|
| DC Motor | `DcMotorManager` | Via `MotionHostModule` |
| Stepper | `StepperManager` | `StepperHostModule` |
| Servo | `ServoManager` | `ServoHostModule` |

### Step 1: Define Commands

```python
# In COMMANDS dict
"CMD_BRUSHLESS_ATTACH": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "Attach a brushless motor (ESC).",
    "payload": {
        "motor_id": {"type": "int", "required": True},
        "pwm_pin": {"type": "int", "required": True},
        "min_us": {"type": "int", "required": False, "default": 1000},
        "max_us": {"type": "int", "required": False, "default": 2000},
    },
},
"CMD_BRUSHLESS_SET_THROTTLE": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "Set brushless motor throttle (0-100%).",
    "payload": {
        "motor_id": {"type": "int", "required": True},
        "throttle_pct": {"type": "float", "required": True},
    },
},
```

### Step 2: Create MCU Driver

```cpp
// firmware/mcu/include/motor/BrushlessManager.h

#pragma once
#include <ESP32Servo.h>

class BrushlessManager {
public:
    static constexpr int MAX_MOTORS = 4;

    bool attach(uint8_t id, uint8_t pwmPin, uint16_t minUs, uint16_t maxUs);
    void setThrottle(uint8_t id, float throttlePct);
    void arm(uint8_t id);
    void disarm(uint8_t id);

private:
    struct Motor {
        Servo esc;
        bool attached = false;
        uint16_t minUs = 1000;
        uint16_t maxUs = 2000;
    };
    Motor motors_[MAX_MOTORS];
};
```

### Step 3: Create Handler

Create `BrushlessHandler.h` or add to existing motor handler:

```cpp
// firmware/mcu/include/command/handlers/BrushlessHandler.h

#pragma once
#include "command/ICommandHandler.h"
#include "motor/BrushlessManager.h"

class BrushlessHandler : public ICommandHandler {
public:
    BrushlessHandler(BrushlessManager& manager) : manager_(manager) {}

    const char* name() const override { return "BrushlessHandler"; }

    bool canHandle(CmdType cmd) const override {
        switch (cmd) {
            case CmdType::BRUSHLESS_ATTACH:
            case CmdType::BRUSHLESS_SET_THROTTLE:
                return true;
            default:
                return false;
        }
    }

    void handle(CmdType cmd, JsonVariantConst payload, CommandContext& ctx) override {
        switch (cmd) {
            case CmdType::BRUSHLESS_ATTACH:    handleAttach(payload, ctx);    break;
            case CmdType::BRUSHLESS_SET_THROTTLE: handleSetThrottle(payload, ctx); break;
            default: break;
        }
    }

private:
    BrushlessManager& manager_;

    void handleAttach(JsonVariantConst payload, CommandContext& ctx) {
        int motorId = payload["motor_id"] | 0;
        int pwmPin = payload["pwm_pin"] | 0;
        int minUs = payload["min_us"] | 1000;
        int maxUs = payload["max_us"] | 2000;

        bool ok = manager_.attach(motorId, pwmPin, minUs, maxUs);

        JsonDocument resp;
        resp["motor_id"] = motorId;
        ctx.sendAck("CMD_BRUSHLESS_ATTACH", ok, resp);
    }

    void handleSetThrottle(JsonVariantConst payload, CommandContext& ctx) {
        int motorId = payload["motor_id"] | 0;
        float throttle = payload["throttle_pct"] | 0.0f;

        manager_.setThrottle(motorId, throttle);

        JsonDocument resp;
        resp["motor_id"] = motorId;
        resp["throttle_pct"] = throttle;
        ctx.sendAck("CMD_BRUSHLESS_SET_THROTTLE", true, resp);
    }
};
```

### Step 4: Create Host Module

```python
# host/mara_host/motor/brushless.py

from mara_host.command.client import MaraClient
from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import CommandHostModule


class BrushlessHostModule(CommandHostModule):
    """
    Host-side wrapper for brushless motor (ESC) commands.
    """

    module_name = "brushless"

    def __init__(self, bus: EventBus, client: MaraClient) -> None:
        super().__init__(bus, client)

    async def attach(
        self,
        motor_id: int,
        pwm_pin: int,
        min_us: int = 1000,
        max_us: int = 2000,
    ) -> None:
        await self._client.cmd_brushless_attach(
            motor_id=motor_id,
            pwm_pin=pwm_pin,
            min_us=min_us,
            max_us=max_us,
        )

    async def set_throttle(self, motor_id: int, throttle_pct: float) -> None:
        await self._client.cmd_brushless_set_throttle(
            motor_id=motor_id,
            throttle_pct=throttle_pct,
        )

    async def arm(self, motor_id: int) -> None:
        """Arm ESC by setting minimum throttle."""
        await self.set_throttle(motor_id, 0.0)

    async def disarm(self, motor_id: int) -> None:
        """Disarm ESC."""
        await self.set_throttle(motor_id, 0.0)
```

---

## Adding a Host Module

Host modules wrap MaraClient methods into clean, domain-specific APIs.

### Module Types

| Type | Base Class | Purpose |
|------|------------|---------|
| Command Module | `CommandHostModule` | Wraps robot commands |
| Event Module | `EventHostModule` | Processes EventBus events |
| Standalone Module | (none) | Independent functionality (e.g., CameraModule) |

### Command Module Template

```python
# host/mara_host/my_domain/my_module.py

from dataclasses import dataclass
from typing import Optional
from mara_host.command.client import MaraClient
from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import CommandHostModule


@dataclass
class MyModuleConfig:
    """Configuration with sensible defaults."""
    default_id: int = 0
    timeout_s: float = 1.0


class MyHostModule(CommandHostModule):
    """
    Host-side module for [domain description].

    Wraps CMD_MY_* commands for cleaner API.
    """

    module_name = "my_module"

    def __init__(
        self,
        bus: EventBus,
        client: MaraClient,
        config: Optional[MyModuleConfig] = None,
    ) -> None:
        super().__init__(bus, client)
        self._config = config or MyModuleConfig()

    async def do_something(self, param: int) -> dict:
        """
        Perform an action.

        Args:
            param: Description of parameter

        Returns:
            Response from MCU
        """
        return await self._client.cmd_my_command(
            id=self._config.default_id,
            param=param,
        )

    async def get_status(self) -> dict:
        """Get current status."""
        return await self._client.cmd_my_status()
```

### Event Module Template

```python
# host/mara_host/my_domain/event_processor.py

from typing import List
from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import EventHostModule


class MyEventProcessor(EventHostModule):
    """
    Processes events from EventBus.

    Subscribes to raw events and publishes processed events.
    """

    module_name = "my_processor"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self._state = {}

    def subscriptions(self) -> List[str]:
        """Topics this module subscribes to."""
        return [
            "telemetry.raw",
            "sensor.my_sensor",
        ]

    def _on_telemetry_raw(self, msg: dict) -> None:
        """Handle raw telemetry events."""
        # Process and republish
        processed = self._process(msg)
        self._bus.publish("telemetry.processed", processed)

    def _on_sensor_my_sensor(self, msg: dict) -> None:
        """Handle sensor events."""
        self._state["last_reading"] = msg
        self._bus.publish("sensor.my_sensor.processed", msg)

    def _process(self, msg: dict) -> dict:
        """Transform raw message."""
        return {"value": msg.get("raw_value", 0) * 2}
```

### Standalone Module Template

For modules that don't need robot commands or event bus:

```python
# host/mara_host/my_domain/standalone.py

import threading
from typing import Callable, Optional


class MyStandaloneModule:
    """
    Standalone module with threading support.

    Similar to CameraModule - manages its own lifecycle.
    """

    def __init__(
        self,
        url: str,
        callback: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self.url = url
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start background processing."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop background processing."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            data = self._fetch_data()
            if data and self._callback:
                self._callback(data)

    def _fetch_data(self) -> Optional[dict]:
        """Fetch data from source."""
        # Implementation here
        pass
```

---

## Adding a Service

Services contain business logic separate from CLI presentation.

### Service Guidelines

1. **No CLI dependencies** - Services return data, not formatted output
2. **No robot connection required** - Operate on config, files, APIs
3. **Testable in isolation** - Unit tests without hardware

### Service Template

```python
# host/mara_host/services/my_service/my_service.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class MyResult:
    """Result data structure."""
    success: bool
    message: str
    data: Optional[dict] = None


class MyService:
    """
    Service for [domain description].

    Business logic extracted from CLI commands.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or Path("config.json")

    def validate(self) -> List[str]:
        """
        Validate configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self._config_path.exists():
            errors.append(f"Config not found: {self._config_path}")

        # Add more validation...

        return errors

    def process(self, input_data: dict) -> MyResult:
        """
        Process input data.

        Args:
            input_data: Data to process

        Returns:
            MyResult with success status and data
        """
        try:
            result = self._do_processing(input_data)
            return MyResult(success=True, message="OK", data=result)
        except Exception as e:
            return MyResult(success=False, message=str(e))

    def _do_processing(self, data: dict) -> dict:
        """Internal processing logic."""
        # Implementation here
        return {"processed": True}
```

### Service Directory Structure

```
services/
├── __init__.py
├── my_service/
│   ├── __init__.py
│   ├── my_service.py      # Main service class
│   ├── models.py          # Data structures
│   └── utils.py           # Helper functions
```

### Using Service in CLI

```python
# cli/commands/my_command.py

from mara_host.services.my_service import MyService

def cmd_validate(args: argparse.Namespace) -> int:
    service = MyService()
    errors = service.validate()

    if errors:
        for error in errors:
            console.print(f"[red]✗[/red] {error}")
        return 1

    console.print("[green]✓[/green] Validation passed")
    return 0
```

---

## Quick Reference

### File Locations

| Component | Host Location | MCU Location |
|-----------|---------------|--------------|
| Transport | `transport/*.py` | `transport/*.h` |
| Sensor | `sensor/*.py` | `sensor/*.h`, `handlers/SensorHandler.h` |
| Motor | `motor/*.py` | `motor/*.h`, `handlers/*MotorHandler.h` |
| Host Module | `{domain}/*.py` | N/A |
| Service | `services/{name}/*.py` | N/A |

### Common Imports

```python
# For command modules
from mara_host.command.client import MaraClient
from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import CommandHostModule, EventHostModule

# For transports
from mara_host.transport.async_base_transport import AsyncBaseTransport
from mara_host.core import protocol

# For services
from dataclasses import dataclass
from pathlib import Path
```

### Regenerate After Changes

```bash
# After editing platform_schema.py
mara generate all

# Build firmware
make build-mcu

# Run tests
make test
```

---

## See Also

- [ADDING_COMMANDS.md](./ADDING_COMMANDS.md) - Command protocol extension
- [CODEGEN.md](./CODEGEN.md) - Code generation system
- [COMPOSITION.md](./COMPOSITION.md) - Architecture patterns
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System overview
