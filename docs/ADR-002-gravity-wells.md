# ADR-002: Splitting Gravity Well Files

## Status
Proposed

## Context

The MARA codebase has grown to 53k+ lines across 518 files. Code review identified several "gravity well" files that concentrate complexity and will become maintenance bottlenecks:

| File | Lines | Risk |
|------|-------|------|
| `platform_schema.py` | 1853 | Source of truth, change magnet |
| `send_all.py` | 802 | Benchmark orchestration |
| `pin_service.py` | 491 | Business logic concentration |
| `build.py` | 486 | CLI command sprawl |
| `logs.py` | 443 | CLI command sprawl |
| `plotting.py` | 463 | Visualization logic |
| `client.py` | 415 | Protocol complexity |

Additionally, C++ headers like `ControlHandler.h` (299 lines) have logic that should move to `.cpp` files.

---

## Decision

### Phase 1: Split `platform_schema.py` (Priority: Critical)

**Current structure** (1853 lines, single file):
```
platform_schema.py
├── OUTPUT PATHS (15 lines)
├── PINS loading (17 lines)
├── VERSION/CAPABILITIES (25 lines)
├── COMMANDS (1420 lines) ← bulk of file
├── TELEMETRY_SECTIONS (62 lines)
├── BINARY_COMMANDS (51 lines)
├── CAN definitions (148 lines)
└── GPIO_CHANNELS (93 lines)
```

**New structure**:
```
tools/
├── platform_schema.py      # Thin facade (re-exports for backwards compat)
└── schema/
    ├── __init__.py         # Public exports
    ├── paths.py            # Output path constants (~20 lines)
    ├── version.py          # VERSION, CAPABILITIES (~30 lines)
    ├── pins.py             # PINS loading (~25 lines)
    ├── commands/           # Command definitions by domain
    │   ├── __init__.py     # Combines all command dicts
    │   ├── safety.py       # Safety/state machine commands
    │   ├── motion.py       # Velocity, differential drive
    │   ├── gpio.py         # GPIO, PWM commands
    │   ├── servo.py        # Servo commands
    │   ├── stepper.py      # Stepper commands
    │   ├── dc_motor.py     # DC motor commands
    │   ├── sensor.py       # Encoder, IMU, ultrasonic
    │   ├── control.py      # Control kernel, observer
    │   └── telemetry_cmd.py # Telemetry config commands
    ├── telemetry.py        # TELEMETRY_SECTIONS (~70 lines)
    ├── binary.py           # BINARY_COMMANDS (~60 lines)
    ├── can.py              # CAN_* definitions (~160 lines)
    └── gpio_channels.py    # GPIO_CHANNELS (~100 lines)
```

**Benefits**:
- Each file < 200 lines (except commands/ which splits further)
- Domain experts can own their command definitions
- Easier to test individual schemas
- Cleaner git history (changes isolated to relevant files)

---

### Phase 2: Split CLI Command Files

Follow the established pattern from `test/`, `run/`, `calibrate/` splits.

**`build.py` (486 lines) → `build/`**:
```
cli/commands/build/
├── __init__.py         # register()
├── _common.py          # Shared utilities
├── firmware.py         # cmd_firmware
├── host.py             # cmd_host
├── all.py              # cmd_all
└── clean.py            # cmd_clean
```

**`logs.py` (443 lines) → `logs/`**:
```
cli/commands/logs/
├── __init__.py
├── _common.py          # Log parsing utilities
├── list.py             # cmd_list
├── view.py             # cmd_view
├── export.py           # cmd_export
└── clean.py            # cmd_clean
```

---

### Phase 3: Split Services

**`pin_service.py` (491 lines) → `pins/`**:
```
services/pins/
├── __init__.py         # PinService facade
├── validation.py       # Conflict detection, validation rules
├── recommendations.py  # Pin recommendations by use case
├── wizards.py          # Interactive wizard logic
└── models.py           # PinConflict, PinRecommendation dataclasses
```

---

### Phase 4: Split `client.py`

**`client.py` (415 lines)**:

The client is already using mixins. Extract to separate files:

```
command/
├── client.py           # MaraClient core (~150 lines)
├── client_base.py      # BaseMaraClient (~100 lines)
├── mixins/
│   ├── __init__.py
│   ├── commands.py     # MaraCommandsMixin (generated)
│   ├── binary.py       # BinaryProtocolMixin
│   └── telemetry.py    # TelemetryMixin
└── protocol.py         # Frame encoding (already separate)
```

---

### Phase 5: Tighten C++ Headers

Move implementation from headers to `.cpp` files:

| Header | Current | Target |
|--------|---------|--------|
| `ControlHandler.h` | 299 lines | < 50 lines (interface only) |
| `MotionHandler.h` | ~200 lines | < 40 lines |
| `SensorHandler.h` | ~150 lines | < 30 lines |

Create corresponding `.cpp` files in `src/command/handlers/`.

---

### Phase 6: Other Large Files (Lower Priority)

| File | Lines | Action |
|------|-------|--------|
| `send_all.py` | 802 | Split by command category |
| `plotting.py` | 463 | Split by plot type (time_series, histogram, etc.) |

---

## Implementation Order

```
1. Phase 1: platform_schema.py → schema/ subpackage
   - Most critical, highest impact
   - Unblocks generator improvements

2. Phase 2: build.py, logs.py → subpackages
   - Follows established CLI pattern
   - Low risk

3. Phase 3: pin_service.py → services/pins/
   - Business logic isolation
   - Improves testability

4. Phase 4: client.py → mixins extraction
   - Protocol clarity
   - Moderate risk (core code path)

5. Phase 5: C++ header cleanup
   - Compile-time improvements
   - Separate PR for firmware changes

6. Phase 6: plotting.py, send_all.py
   - Lower priority
   - Nice to have
```

---

## Backwards Compatibility

All splits will maintain backwards compatibility via re-exports:

```python
# platform_schema.py (after split)
"""Backwards-compatible facade for platform schema."""
from .schema import (
    COMMANDS,
    BINARY_COMMANDS,
    TELEMETRY_SECTIONS,
    GPIO_CHANNELS,
    CAN_MESSAGES,
    PINS,
    VERSION,
    CAPABILITIES,
    # ... all exports
)

# Deprecated: import from schema/ directly
__all__ = [...]
```

---

## Success Criteria

- [ ] No file > 500 lines in tools/schema/
- [ ] No file > 300 lines in cli/commands/*/
- [ ] No file > 200 lines in services/*/
- [ ] All generators still work
- [ ] All tests pass
- [ ] Import paths documented

---

## References

- [CODEGEN.md](./CODEGEN.md) - Code generation ownership
- [COMPOSITION.md](./COMPOSITION.md) - Architecture patterns
- [EXTENDING.md](./EXTENDING.md) - Extension guide
