# Composition & Dependency Guide

This document defines the composition model (Robot vs Runtime vs Services)
and dependency rules for mara_host. For system architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

**Related:** [ADR-001: Architectural Consolidation](./ADR-001-consolidation.md)

## Core Abstractions

mara_host uses three core abstractions for different use cases:

### Robot (robot.py)

The **canonical entry point** for connecting to a robot.

**Owns:**
- Transport initialization (serial, WiFi, CAN)
- EventBus instance
- Command client facade

**Use when:**
- Direct robot control without control loop
- Simple scripts and experiments
- Jupyter notebooks
- One-off commands

```python
async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
    await robot.motion.set_velocity(0.1, 0.0)
```

### Runtime (runtime/runtime.py)

**Optional** control loop framework that wraps Robot.

**Owns:**
- Fixed-rate tick loop (tick_hz)
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

### Services (services/)

**Business logic** extracted from CLI commands.

**Owns:**
- Pin management (PinService)
- Build orchestration (FirmwareBuildService)
- Code generation (CodeGeneratorService)
- Recording/replay (RecordingService)
- Testing (TestService)

**Use when:**
- Building CLI commands
- REST/gRPC APIs
- Operations not requiring real-time control
- Reusable business logic

```python
from mara_host.services.pins import PinService

service = PinService()
conflicts = service.detect_conflicts()
rec = service.recommend_motor_pins("LEFT")
```

**Key principle:** Services do NOT require a robot connection.
They operate on configuration, files, and external resources.

---

## Dependency Rules

These rules define what each package may and must not import from.

| Package | May depend on | Must NOT depend on |
|---------|---------------|-------------------|
| `cli/` | `services/` | `tools/` (for business logic) |
| `services/` | `tools/`, `config/` | `cli/`, `runtime/` |
| `runtime/` | `robot.py` | - |
| `robot.py` | `transport/`, `core/` | `runtime/` |
| `tools/` | (none) | anything |
| `research/` | `services/`, `robot/` | should not own core workflows |

### Rationale

- **cli → services:** CLI provides UX; services provide logic
- **services → tools:** Services can use pure data/I/O utilities
- **runtime → robot:** Runtime wraps Robot, not the other way
- **robot.py → not runtime:** Robot should work without runtime overhead
- **tools → nothing:** Tools are leaf nodes (pure data and I/O)

---

## Canonical Paths

These are the standard ways to implement common patterns.

### Adding a new CLI command

1. Add business logic to appropriate service (e.g., `services/pins/PinService`)
2. Service methods return **data structures**, not formatted output
3. Add CLI handler in `cli/commands/` that:
   - Calls service methods
   - Owns argparse registration
   - Owns Rich formatting and interactive UX
   - Returns exit codes

### Adding a new pin business rule

1. Add method to `PinService` (e.g., `detect_conflicts()`)
2. Method returns data structure (e.g., `list[PinConflict]`)
3. Update CLI `cmd_conflicts()` to call new method
4. CLI formats the result for display

### Adding a new camera config field

1. Add field to `CameraConfig` in `camera/models.py`
2. Add to `from_dict()` and `to_dict()` methods
3. Update firmware if needed
4. All other camera files import from `models.py`

### Adding a new model/dataclass

- If firmware-related: `camera/models.py` or appropriate `models.py`
- If service-related: Define in the service module
- If shared across modules: Consider `core/` or dedicated `models/` package

---

## Module Ownership

### camera/

| File | Owns |
|------|------|
| `models.py` | All camera types (FrameSize, CaptureMode, CameraConfig, etc.) |
| `control.py` | HTTP API client for ESP32-CAM |
| `module.py` | High-level CameraModule with threading |
| `presets.py` | Preset configurations |
| `__init__.py` | Clean exports (no aliases) |

### services/pins/

| Layer | Owns |
|-------|------|
| `tools/pins.py` | Data (ESP32_PINS), I/O (load/save), utilities (cap_str) |
| `services/pins/PinService` | Validation, conflict detection, recommendations |
| `cli/commands/pins/` | Rich formatting, interactive wizards, argparse |

### tools/

Tools are **pure utilities** with no business logic:

- Data structures and constants
- File I/O operations
- Format conversions
- Code generation templates

Tools should NOT contain:
- Validation rules (→ services)
- Command handlers (→ cli)
- Interactive prompts (→ cli)

---

## Anti-Patterns (Do NOT Do)

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

### Duplicate models across files

```python
# BAD - same enum in two files
# camera/models.py
class FrameSize(IntEnum): ...

# camera/control.py
class FrameSize(IntEnum): ...  # Different values!
```

```python
# GOOD - single source of truth
# camera/models.py
class FrameSize(IntEnum): ...

# camera/control.py
from .models import FrameSize  # Import canonical version
```

### Bypass services from CLI

```python
# BAD - CLI using tools directly for business logic
from mara_host.tools.pins import ESP32_PINS, FLASH_PINS

def cmd_validate(args):
    for gpio in pins.values():
        if gpio in FLASH_PINS:  # Duplicated validation logic
            ...
```

```python
# GOOD - CLI uses service
from mara_host.services.pins import PinService

def cmd_validate(args):
    conflicts = PinService().detect_conflicts()
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

### Return formatted strings from services

```python
# BAD - service returns formatted output
def validate(self) -> str:
    return "✓ All pins valid"  # Coupling to display format
```

```python
# GOOD - service returns data structure
def validate(self) -> list[PinConflict]:
    return conflicts  # CLI formats as needed
```

---

## Testing Guidelines

### Unit Testing Services

Services should be testable without CLI or robot connection:

```python
def test_detect_conflicts_i2c_incomplete():
    service = PinService()
    service.assign("I2C_SDA", 21)
    # Missing I2C_SCL

    conflicts = service.detect_conflicts()
    assert any(c.conflict_type == "i2c_incomplete" for c in conflicts)
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

## References

- [ADR-001: Architectural Consolidation Decisions](./ADR-001-consolidation.md)
- ESP32 Technical Reference Manual
- ESP32-CAM firmware framesize_t definition
