# Composition & Dependency Guide

<div align="center">

**How components fit together in MARA**

*Robot vs Runtime vs Services*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Core Abstractions

MARA uses three core abstractions for different use cases:

---

### Robot (`robot.py`)

The **canonical entry point** for connecting to a robot.

**Owns:**
- Transport initialization (serial, WiFi, CAN)
- EventBus instance
- Client and services composition

**Use when:**
- Direct robot control without control loop
- Simple scripts and experiments
- Jupyter notebooks
- One-off commands

```python
async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
    await robot.motion.set_velocity(0.1, 0.0)
    await asyncio.sleep(2.0)
    await robot.motion.stop()
    await robot.disarm()
```

---

### Runtime (`runtime/runtime.py`)

**Optional** control loop framework that wraps Robot.

**Owns:**
- Fixed-rate tick loop (`tick_hz`)
- Module lifecycle management
- Telemetry aggregation and callbacks

**Use when:**
- Fixed-rate control loop required
- Multiple modules need coordinated lifecycle
- Consistent telemetry callback patterns needed

```python
runtime = Runtime(robot, tick_hz=50)

@runtime.on_tick
async def control(dt):
    # Called at 50Hz
    await robot.motion.set_velocity(0.1, 0.0)

runtime.start()
```

**Important:** Runtime is optional. Simple robot control does not require it.

---

### Services (`services/`)

**Business logic** layer between API and Client.

**Control Services** (`services/control/`):
- GpioService, MotionService, ServoService
- MotorService, StateService
- Track hardware state, return `ServiceResult`

**Other Services:**
- PinService: GPIO pin management, conflict detection
- TestService: Robot self-test suite
- RecordingService: Session recording and replay
- CodeGeneratorService: Firmware build orchestration

```python
from mara_host.services.control import MotionService

# Services return ServiceResult, not exceptions
result = await motion_service.set_velocity(0.5, 0.0)
if result.ok:
    print(f"Velocity set: {result.data}")
else:
    print(f"Error: {result.error}")
```

**Key principle:** Control services require a client connection. Other services (pins, testing) do NOT require a robot connection—they operate on configuration, files, and external resources.

---

## Layer Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│  User Application                                                │
├─────────────────────────────────────────────────────────────────┤
│  API Layer (api/)                                               │
│  └── Validation, exceptions, user-facing interface              │
├─────────────────────────────────────────────────────────────────┤
│  Services Layer (services/control/)                             │
│  └── Business logic, state tracking, ServiceResult              │
├─────────────────────────────────────────────────────────────────┤
│  Client Layer (command/client.py)                               │
│  └── Routing, handshake, connection management                  │
├─────────────────────────────────────────────────────────────────┤
│  Commander Layer (command/coms/reliable_commander.py)           │
│  └── ALL commands (reliable & streaming), events, metrics       │
├─────────────────────────────────────────────────────────────────┤
│  Transport Layer (transport/)                                   │
│  └── Raw bytes, connection lifecycle, frame buffering           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependency Rules

These rules define what each package may and must not import from.

| Package | May depend on | Must NOT depend on |
|:--------|:--------------|:-------------------|
| `api/` | `services/`, `core/` | `command/`, `transport/` |
| `services/control/` | `command/`, `core/` | `api/`, `runtime/` |
| `cli/` | `services/` | `tools/` (for business logic) |
| `runtime/` | `robot.py` | - |
| `robot.py` | `transport/`, `command/`, `services/`, `core/` | `runtime/` |
| `command/` | `core/`, `transport/` | `api/`, `services/` |
| `tools/` | (none) | anything |

### Rationale

- **api → services:** API validates and delegates to services
- **services → command:** Services call client for hardware operations
- **cli → services:** CLI provides UX; services provide logic
- **runtime → robot:** Runtime wraps Robot, not the other way
- **robot.py → not runtime:** Robot should work without runtime overhead
- **tools → nothing:** Tools are leaf nodes (pure data and I/O)

---

## Canonical Paths

Standard ways to implement common patterns.

### Adding a new API method

1. Add service method in `services/control/*_service.py`
2. Service method returns `ServiceResult`
3. Add API method in `api/*.py` that:
   - Validates inputs
   - Calls service method
   - Raises exception if `not result.ok`

### Adding a new CLI command

1. Add business logic to appropriate service
2. Service methods return **data structures**, not formatted output
3. Add CLI handler in `cli/commands/` that:
   - Calls service methods
   - Owns argparse registration
   - Owns Rich formatting and interactive UX
   - Returns exit codes

### Adding a new hardware component

1. Define in `tools/schema/hardware/_sensors.py`
2. Run `mara generate all`
3. Add service in `services/control/`
4. Add API class in `api/`

---

## Module Ownership

### services/control/

| Service | Owns |
|:--------|:-----|
| `gpio_service.py` | GPIO channel state, digital I/O |
| `motion_service.py` | Velocity commands, motion limits |
| `servo_service.py` | Servo channel state, angle/duty commands |
| `motor_service.py` | DC motor configuration, PID tuning |
| `state_service.py` | Robot state machine (arm/disarm/activate) |

### api/

| API | Owns |
|:----|:-----|
| `gpio.py` | User-facing GPIO class with validation |
| `servo.py` | User-facing Servo class with validation |
| `pwm.py` | User-facing PWM class with validation |
| `dc_motor.py` | User-facing DCMotor class with validation |

### command/

| Component | Owns |
|:----------|:-----|
| `client.py` | MaraClient coordinator, routing |
| `coms/reliable_commander.py` | Command dispatch, ACKs, retries, events |
| `coms/connection_monitor.py` | Health monitoring, heartbeat |

---

## Anti-Patterns (Do NOT Do)

### API calling client directly

```python
# BAD - API bypasses service layer
class GPIO:
    async def write(self, channel, value):
        await self._robot.client.cmd_gpio_write(channel=channel, value=value)
```

```python
# GOOD - API routes through service
class GPIO:
    async def write(self, channel, value):
        result = await self._service.write(channel, value)
        if not result.ok:
            raise RuntimeError(result.error)
```

### Service raising exceptions

```python
# BAD - service raises instead of returning result
class GpioService:
    async def write(self, channel, value):
        if error:
            raise RuntimeError("Failed")  # ← Should return ServiceResult
```

```python
# GOOD - service returns ServiceResult
class GpioService:
    async def write(self, channel, value):
        if error:
            return ServiceResult.failure(error="Failed")
        return ServiceResult.success(data={"channel": channel})
```

### Put business logic in CLI handlers

```python
# BAD - validation logic in CLI
def cmd_validate(args):
    pins = load_pins()
    for name, gpio in pins.items():
        if gpio in FLASH_PINS:  # Business logic!
            print_error(...)
```

```python
# GOOD - delegate to service
def cmd_validate(args):
    service = PinService()
    conflicts = service.detect_conflicts()  # Service owns logic
    for c in conflicts:
        print_error(c.message)  # CLI owns formatting
```

### Make Runtime mandatory

```python
# BAD - requiring runtime for simple control
runtime = Runtime(robot, tick_hz=50)
runtime.start()  # Overhead for one-off command
await robot.arm()
```

```python
# GOOD - use Robot directly for simple cases
async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
```

---

## Testing Guidelines

### Unit Testing Services

Services should be testable without CLI or robot connection:

```python
def test_motion_service_clamps_velocity():
    mock_client = Mock()
    service = MotionService(mock_client)

    await service.set_velocity(vx=10.0, omega=0.0)  # Exceeds limit

    # Verify clamping
    mock_client.send_stream.assert_called_with(
        "CMD_SET_VEL",
        {"vx": 1.0, "omega": 0.0},  # Clamped to limit
        request_ack=False,
        binary=True,
    )
```

### Unit Testing API

API tests verify validation and exception raising:

```python
async def test_gpio_write_unregistered_raises():
    api = GPIO(mock_service)

    with pytest.raises(ValueError, match="not registered"):
        await api.write(channel=99, value=1)
```

### Integration Testing CLI

CLI tests verify formatting and exit codes:

```python
def test_cmd_validate_returns_error_on_flash_pin(tmp_path):
    # Setup: create pins.json with flash pin
    # Run: cmd_validate(args)
    # Assert: exit code is 1
```

---

## Summary

| Abstraction | Purpose | When to Use |
|:------------|:--------|:------------|
| **Robot** | Connection facade | Direct control, scripts |
| **Runtime** | Tick loop framework | Fixed-rate control |
| **Services** | Business logic | Reusable operations |
| **API** | User-facing interface | External consumers |
| **Commander** | Command dispatch | Internal (all commands) |

**Golden rule:** API validates → Services process → Client routes → Commander dispatches.

---

<div align="center">

*See [ARCHITECTURE.md](./ARCHITECTURE.md) for system architecture*

</div>
