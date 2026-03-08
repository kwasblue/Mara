# Extending MARA

<div align="center">

**Add new transports, sensors, motors, and modules**

*Complete guide to platform extension*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

**Prerequisites:** Read [ADDING_COMMANDS.md](./ADDING_COMMANDS.md) first for command/protocol extension.

---

## Table of Contents

1. [Adding a New Transport](#adding-a-new-transport)
2. [Adding a New Sensor](#adding-a-new-sensor)
3. [Adding a New Motor Type](#adding-a-new-motor-type)
4. [Adding a Service](#adding-a-service)
5. [Adding an API Class](#adding-an-api-class)

---

## Adding a New Transport

Transports handle communication between the Python host and ESP32 MCU.

### Existing Transports

| Transport | File | Use Case |
|:----------|:-----|:---------|
| Serial | `serial_transport.py` | USB connection |
| TCP | `tcp_transport.py` | WiFi connection |
| CAN | `can_transport.py` | CAN bus |
| Bluetooth | `bluetooth_transport.py` | Bluetooth Classic |
| MQTT | `mqtt/` | Multi-node fleet control |

### Step 1: Create Transport Class

Extend `StreamTransport` (for byte-stream transports) or `AsyncBaseTransport`:

```python
# transport/websocket_transport.py

import asyncio
from typing import Optional
from mara_host.core import protocol
from mara_host.transport.stream_transport import StreamTransport

class WebSocketTransport(StreamTransport):
    """
    WebSocket transport for browser-based control.
    """

    def __init__(self, url: str, reconnect_delay: float = 5.0) -> None:
        super().__init__()
        self.url = url
        self.reconnect_delay = reconnect_delay
        self._ws = None

    @property
    def is_connected(self) -> bool:
        return self._ws is not None

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        import websockets
        self._ws = await websockets.connect(self.url)

    def _send_bytes_sync(self, data: bytes) -> None:
        """Synchronous send (called via executor)."""
        if self._ws:
            asyncio.run(self._ws.send(data))

    async def _read_loop(self) -> None:
        """Background read loop."""
        async for message in self._ws:
            if isinstance(message, bytes):
                self._rx_buffer.extend(message)
                protocol.extract_frames(self._rx_buffer, self._handle_frame)
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

Update the robot factory to support the new transport:

```python
# In robot.py or factory method
if uri.startswith("ws://"):
    from mara_host.transport.websocket_transport import WebSocketTransport
    transport = WebSocketTransport(uri)
```

---

## Adding a New Sensor

Adding a sensor requires changes on both MCU (C++) and Host (Python) sides.

### Existing Sensors

| Sensor | MCU Manager | Host Service |
|:-------|:------------|:-------------|
| Encoder | `EncoderManager` | Via telemetry |
| IMU | `ImuManager` | Via telemetry |
| Ultrasonic | `UltrasonicManager` | Via telemetry |

### Step 1: Define Commands in Schema

Edit `host/mara_host/tools/schema/commands/_sensors.py`:

```python
# In SENSOR_COMMANDS dict
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

For high-rate sensor data, add a telemetry section in `host/mara_host/tools/schema/telemetry.py`:

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
void handleLidarAttach(JsonVariantConst payload, CommandContext& ctx) {
    int sensorId = payload["sensor_id"] | 0;
    int rxPin = payload["rx_pin"] | 0;
    int txPin = payload["tx_pin"] | 0;

    bool ok = lidar_.attach(sensorId, rxPin, txPin);
    ctx.sendAck("CMD_LIDAR_ATTACH", ok);
}
```

### Step 6: Create Service

```python
# host/mara_host/services/control/lidar_service.py

from mara_host.core.result import ServiceResult

class LidarService:
    """Service for LiDAR sensor operations."""

    def __init__(self, client):
        self.client = client

    async def attach(
        self,
        sensor_id: int,
        rx_pin: int,
        tx_pin: int,
    ) -> ServiceResult:
        ok, error = await self.client.send_reliable(
            "CMD_LIDAR_ATTACH",
            {"sensor_id": sensor_id, "rx_pin": rx_pin, "tx_pin": tx_pin},
        )
        if ok:
            return ServiceResult.success(data={"sensor_id": sensor_id})
        return ServiceResult.failure(error=error or "Failed to attach")

    async def read(self, sensor_id: int) -> ServiceResult:
        ok, error = await self.client.send_reliable(
            "CMD_LIDAR_READ",
            {"sensor_id": sensor_id},
        )
        if ok:
            return ServiceResult.success()
        return ServiceResult.failure(error=error or "Failed to read")
```

### Step 7: Create API Class

```python
# host/mara_host/api/lidar.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.services.control.lidar_service import LidarService

class Lidar:
    """User-facing LiDAR API."""

    def __init__(self, service: "LidarService"):
        self._service = service
        self._attached: dict[int, bool] = {}

    async def attach(
        self,
        sensor_id: int,
        rx_pin: int,
        tx_pin: int,
    ) -> None:
        """Attach a LiDAR sensor."""
        result = await self._service.attach(sensor_id, rx_pin, tx_pin)
        if not result.ok:
            raise RuntimeError(result.error)
        self._attached[sensor_id] = True

    async def read(self, sensor_id: int) -> dict:
        """Read LiDAR distance."""
        if sensor_id not in self._attached:
            raise ValueError(f"Sensor {sensor_id} not attached")
        result = await self._service.read(sensor_id)
        if not result.ok:
            raise RuntimeError(result.error)
        return result.data
```

---

## Adding a New Motor Type

Similar to sensors, motors require MCU driver + host service + API.

### Existing Motors

| Motor | MCU Manager | Host Service |
|:------|:------------|:-------------|
| DC Motor | `DcMotorManager` | `MotorService` |
| Stepper | `StepperManager` | - |
| Servo | `ServoManager` | `ServoService` |

### Step 1: Define Commands

Create a new domain file `host/mara_host/tools/schema/commands/_brushless.py`:

```python
"""Brushless motor (ESC) command definitions."""

BRUSHLESS_COMMANDS: dict[str, dict] = {
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
}
```

Then register in `schema/commands/__init__.py`:

```python
from ._brushless import BRUSHLESS_COMMANDS

COMMANDS: dict[str, dict] = {
    # ... existing domains ...
    **BRUSHLESS_COMMANDS,
}
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

### Step 3: Create Service and API

Follow the same pattern as the sensor example above:
1. Service with `ServiceResult` returns
2. API with validation and exceptions

---

## Adding a Service

Services contain business logic separate from API presentation.

### Service Guidelines

1. **Return `ServiceResult`** - Never raise exceptions
2. **No CLI dependencies** - Services return data, not formatted output
3. **Testable in isolation** - Unit tests without hardware

### Service Template

```python
# host/mara_host/services/control/my_service.py

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mara_host.core.result import ServiceResult

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


class MyService:
    """
    Service for [domain description].

    Business logic extracted from CLI commands.
    """

    def __init__(self, client: "MaraClient") -> None:
        self.client = client
        self._state: dict = {}

    async def my_operation(self, param: int) -> ServiceResult:
        """
        Perform an operation.

        Args:
            param: Description of parameter

        Returns:
            ServiceResult with success/failure
        """
        ok, error = await self.client.send_reliable(
            "CMD_MY_COMMAND",
            {"param": param},
        )

        if ok:
            self._state["last_param"] = param
            return ServiceResult.success(data={"param": param})
        else:
            return ServiceResult.failure(error=error or "Failed")
```

---

## Adding an API Class

API classes provide user-facing interfaces with validation.

### API Guidelines

1. **Validate inputs** - Check before calling service
2. **Raise exceptions** - Convert `ServiceResult.failure` to exceptions
3. **Track local state** - Know what's been configured

### API Template

```python
# host/mara_host/api/my_device.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.services.control.my_service import MyService


class MyDevice:
    """
    User-facing API for [device description].

    Validates inputs and raises exceptions on errors.
    """

    def __init__(self, service: "MyService") -> None:
        self._service = service
        self._configured: set[int] = set()

    async def configure(self, device_id: int, param: int) -> None:
        """
        Configure a device.

        Args:
            device_id: Device identifier (0-3)
            param: Configuration parameter

        Raises:
            ValueError: If device_id is out of range
            RuntimeError: If configuration fails
        """
        if not 0 <= device_id <= 3:
            raise ValueError(f"device_id must be 0-3, got {device_id}")

        result = await self._service.configure(device_id, param)

        if not result.ok:
            raise RuntimeError(result.error)

        self._configured.add(device_id)

    def is_configured(self, device_id: int) -> bool:
        """Check if a device is configured."""
        return device_id in self._configured
```

---

## Quick Reference

### File Locations

| Component | Host Location | MCU Location |
|:----------|:--------------|:-------------|
| Transport | `transport/*.py` | `transport/*.h` |
| Sensor | `services/control/*.py`, `api/*.py` | `sensor/*.h`, `handlers/*.h` |
| Motor | `services/control/*.py`, `api/*.py` | `motor/*.h`, `handlers/*.h` |
| Service | `services/control/*.py` | N/A |
| API | `api/*.py` | N/A |

### Common Imports

```python
# For services
from mara_host.core.result import ServiceResult
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient

# For API classes
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.services.control.my_service import MyService
```

### Layer Flow

```
User → API (validate, exceptions) → Service (logic, ServiceResult)
     → Client (routing) → Commander (dispatch) → Transport (bytes)
```

---

## See Also

- [ADDING_COMMANDS.md](./ADDING_COMMANDS.md) - Command protocol extension
- [CODEGEN.md](./CODEGEN.md) - Code generation system
- [COMPOSITION.md](./COMPOSITION.md) - Architecture patterns
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System overview

---

<div align="center">

*API validates → Service processes → Commander dispatches*

</div>
