# ADR-001: Architectural Consolidation Decisions

**Status:** Accepted
**Date:** 2026-03-07

## Context

The codebase has grown organically, leading to:
- Duplicate model definitions across camera subsystem files
- Business logic scattered across tools/, services/, and cli/ layers
- Unclear boundaries between Robot, Runtime, and Services abstractions

This ADR documents the consolidation decisions to establish clear ownership and eliminate duplication.

---

## Camera Types

### Decision

**Canonical source:** `camera/models.py`

### FrameSize Enum

Use 15-value IntEnum matching ESP32-CAM firmware `framesize_t`:

```python
class FrameSize(IntEnum):
    R96X96 = 0      # 96x96
    QQVGA = 1       # 160x120
    R128X128 = 2    # 128x128
    QCIF = 3        # 176x144
    HQVGA = 4       # 240x176
    R240X240 = 5    # 240x240
    QVGA = 6        # 320x240
    CIF = 7         # 400x296
    HVGA = 8        # 480x320
    VGA = 9         # 640x480
    SVGA = 10       # 800x600
    XGA = 11        # 1024x768
    HD = 12         # 1280x720
    SXGA = 13       # 1280x1024
    UXGA = 14       # 1600x1200
```

### CaptureMode Enum

Use IntEnum matching firmware protocol:

```python
class CaptureMode(IntEnum):
    POLLING = 0     # HTTP polling /jpg endpoint
    STREAMING = 1   # MJPEG stream /stream endpoint
```

### CameraConfig

Use firmware-compatible field names (matching HTTP API):

- `white_balance` (not `awb_enabled`)
- `wb_mode` (not `awb_mode`)
- `exposure_ctrl` (not `aec_enabled`)
- `gain_ctrl` (not `agc_enabled`)

Include serialization methods `from_dict()` and `to_dict()` for HTTP API compatibility.

### Rationale

- **Firmware compatibility:** Values must match ESP32-CAM `framesize_t` for direct API calls
- **Single source of truth:** All camera files import from `models.py`
- **Type safety:** IntEnum prevents integer/string confusion

---

## Pins Ownership

### Decision

Three-layer architecture with clear separation:

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Data + I/O | `tools/pins.py` | ESP32_PINS, load/save, generate_pinout |
| Business Logic | `services/pins/PinService` | Validation, conflicts, recommendations |
| Presentation | `cli/commands/pins.py` | Rich formatting, interactive UX |

### Data Layer (tools/pins.py)

Owns:
- `Capability` enum
- `PinInfo` dataclass
- `ESP32_PINS` dictionary
- Pin group constants: `SAFE_PINS`, `INPUT_ONLY_PINS`, `FLASH_PINS`, `BOOT_PINS`
- I/O functions: `load_pins()`, `save_pins()`, `get_assignments()`
- Utilities: `generate_pinout()`, `cap_str()`

Does NOT own:
- Command handlers (`cmd_*` functions)
- Business logic (validation rules, recommendations)

### Service Layer (services/pins/PinService)

Owns:
- `detect_conflicts()` - Returns `list[PinConflict]`
- `recommend_motor_pins()` - Returns `PinRecommendation`
- `recommend_encoder_pins()` - Returns `PinRecommendation`
- `recommend_i2c_pins()` - Returns `PinRecommendation`
- Assignment operations with validation

Key principle: Methods return **data structures**, not formatted output.

### CLI Layer (cli/commands/pins.py)

Owns:
- Argparse registration
- Rich console formatting
- Interactive wizards (prompts, confirmations)
- Exit codes

Delegates to: `PinService` for all business logic.

### Rationale

- **Testability:** Service layer can be unit tested without CLI
- **Reusability:** Service methods usable from scripts, APIs, notebooks
- **Separation of concerns:** Each layer has a single responsibility

---

## Composition Model

### Decision

Three distinct abstractions with clear purposes:

### Robot (robot.py)

**Role:** Canonical connection facade

**Owns:**
- Transport initialization
- EventBus instance
- Command client

**Use when:**
- Direct robot control without control loop
- Simple scripts and experiments
- Jupyter notebooks

```python
async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
```

### Runtime (runtime/runtime.py)

**Role:** Optional control loop orchestration

**Owns:**
- Fixed-rate tick loop
- Module lifecycle
- Telemetry aggregation

**Use when:**
- Fixed-rate control loop required (tick_hz)
- Module lifecycle management needed
- Consistent telemetry callbacks

```python
runtime = Runtime(robot, tick_hz=50)

@runtime.on_tick
async def control(dt):
    await robot.motion.set_velocity(0.1, 0.0)
```

### Services (services/)

**Role:** Business logic for non-real-time operations

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

```python
from mara_host.services.pins import PinService
conflicts = PinService().detect_conflicts()
```

### Dependency Rules

| Package | May depend on | Must NOT depend on |
|---------|---------------|-------------------|
| cli/ | services/ | tools/ (for business logic) |
| services/ | tools/, config/ | cli/, runtime/ |
| runtime/ | robot.py | - |
| robot.py | transport/, core/ | runtime/ |
| tools/ | (none) | anything |
| research/ | services/, robot/ | (should not own core workflows) |

### Rationale

- **Optional runtime:** Simple use cases shouldn't need control loop overhead
- **Testable services:** Business logic isolated from CLI and transport
- **Clear boundaries:** Each abstraction has a specific purpose

---

## Consequences

### Positive

- Single source of truth for camera types
- Business logic testable without CLI
- Clear architectural boundaries
- Reduced code duplication

### Negative

- Initial migration effort
- Existing code using deprecated imports needs updating

### Migration Path

1. Phase 1: Consolidate camera models (highest risk)
2. Phase 2: Consolidate pins service (cleanest win)
3. Phase 3: Document composition model

---

## References

- ESP32-CAM firmware framesize_t definition
- ESP32 Technical Reference Manual (GPIO capabilities)
