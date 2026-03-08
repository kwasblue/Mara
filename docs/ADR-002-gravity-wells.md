# ADR-002: Splitting Gravity Well Files

## Status
✅ **COMPLETE** (All Phases Finished)

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

### Phase 1: Split `platform_schema.py` (Priority: Critical) ✅ COMPLETE

**Previous structure** (1853 lines, single file):
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

**Current structure** (completed):
```
tools/
└── schema/
    ├── __init__.py         # Public exports
    ├── paths.py            # Output path constants
    ├── version.py          # VERSION, CAPABILITIES
    ├── pins.py             # PINS loading
    ├── commands/           # Command definitions by domain (79 commands total)
    │   ├── __init__.py     # Combines all command dicts
    │   ├── _safety.py      # Safety/state machine (9 commands)
    │   ├── _rates.py       # Loop rates (4 commands)
    │   ├── _control.py     # Signal bus, slots (13 commands)
    │   ├── _motion.py      # Velocity commands (2 commands)
    │   ├── _gpio.py        # LED, GPIO, PWM (7 commands)
    │   ├── _servo.py       # Servo commands (3 commands)
    │   ├── _stepper.py     # Stepper commands (3 commands)
    │   ├── _sensors.py     # Encoder, ultrasonic (5 commands)
    │   ├── _dc_motor.py    # DC motor + PID (5 commands)
    │   ├── _observer.py    # Luenberger observer (6 commands)
    │   ├── _telemetry.py   # Telemetry config (2 commands)
    │   └── _camera.py      # ESP32-CAM over HTTP (20 commands)
    ├── telemetry.py        # TELEMETRY_SECTIONS
    ├── binary.py           # BINARY_COMMANDS
    ├── can.py              # CAN_* definitions
    └── gpio_channels.py    # GPIO_CHANNELS
```

**Benefits achieved**:
- Largest command file is _camera.py at 423 lines (was 1420 combined)
- Domain experts can own their command definitions
- Easier to test individual schemas
- Cleaner git history (changes isolated to relevant files)
- No backwards compatibility shim needed (package takes precedence)

---

### Phase 2: Split CLI Command Files ✅ COMPLETE

**`build.py` → `build/`** (10 modules):
```
cli/commands/build/
├── __init__.py, _common.py, _registry.py
├── clean.py, compile.py, features.py
├── size.py, test.py, upload.py, watch.py
```

**`logs.py` → `logs/`** (10 modules):
```
cli/commands/logs/
├── __init__.py, _common.py, _registry.py
├── delete.py, export.py, list.py
├── search.py, show.py, stats.py, tail.py
```

---

### Phase 3: Split Services ✅ COMPLETE

**`pin_service.py` → `services/pins/`** (6 modules):
```
services/pins/
├── __init__.py         # PinService facade
├── service.py          # Core service logic
├── conflicts.py        # Conflict detection
├── recommendations.py  # Pin recommendations
├── groups.py           # Pin grouping logic
└── models.py           # PinConflict, PinRecommendation
```

---

### Phase 4: Client Architecture ✅ COMPLETE

**`client.py` (597 lines)** - Already uses mixin pattern:
```
command/
├── client.py           # MaraClient with mixin composition
├── binary_mixin.py     # BinaryProtocolMixin
├── binary_commands.py  # Generated binary command helpers
├── factory.py          # MaraClientFactory
├── interfaces.py       # IMaraClient interface
└── command_streamer.py # Streaming support
```

---

### Phase 5: C++ Headers ✅ ALREADY OPTIMIZED

Headers are already well-sized (no action needed):

| Header | Actual Lines |
|--------|--------------|
| `ControlHandler.h` | 81 |
| `MotionHandler.h` | 45 |
| `SensorHandler.h` | 52 |
| `SafetyHandler.h` | 61 |
| All 12 handlers | 632 total |

All handlers follow interface-only pattern with implementations in `.cpp`.

---

### Phase 6: Other Large Files (Lower Priority) ✅ COMPLETE

| File | Lines | Action | Result |
|------|-------|--------|--------|
| `send_all.py` | 1072 | Split by concern | `benchmarks/commands/send_all/` (8 files) |
| `plotting.py` | 681 | Split by plot type | `research/plotting/` (9 files) |

**plotting/ structure**:
```
research/plotting/
├── __init__.py       # Re-exports all functions
├── config.py         # DEFAULT_STYLE, apply_style(), create_figure()
├── timeseries.py     # plot_time_series(), plot_multi_series(), plot_telemetry_dashboard()
├── control.py        # plot_setpoint_vs_actual(), plot_control_loop(), plot_step_response()
├── trajectory.py     # plot_trajectory_2d(), plot_pose_trajectory()
├── frequency.py      # plot_fft(), plot_psd(), plot_bode()
├── distribution.py   # plot_histogram(), plot_latency_cdf(), plot_latency_stats()
├── imu.py            # plot_imu_data()
└── utils.py          # save_figure(), show()
```

**send_all/ structure**:
```
benchmarks/commands/send_all/
├── __init__.py       # Re-exports
├── __main__.py       # Module entry point
├── commands.py       # Command constants and category helpers
├── types.py          # CmdResult, RunContext, PayloadSpec types
├── helpers.py        # Transport discovery, payload loading, skip logic
├── client.py         # build_client(), warmup_client(), send_cmd()
├── run.py            # Main run logic and state machine
└── cli.py            # build_argparser(), list_commands(), main()
```

---

## Implementation Order

All phases complete:

```
1. Phase 1: platform_schema.py → schema/ ✅ COMPLETE
   - schema/commands/ has 12 domain files (79 commands)

2. Phase 2: build.py, logs.py → subpackages ✅ COMPLETE
   - build/ (10 modules), logs/ (10 modules)

3. Phase 3: pin_service.py → services/pins/ ✅ COMPLETE
   - 6 focused modules

4. Phase 4: client.py → mixin architecture ✅ COMPLETE
   - Already uses mixin pattern, factory added

5. Phase 5: C++ headers ✅ ALREADY OPTIMIZED
   - All handlers < 100 lines each

6. Phase 6: plotting.py, send_all.py ✅ COMPLETE
   - plotting/ (9 files), send_all/ (8 files)
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

- [x] No file > 500 lines in tools/schema/ (largest: _camera.py at 423 lines)
- [x] No file > 300 lines in cli/commands/*/ (test/, run/, calibrate/, build/, logs/ all split)
- [x] No file > 200 lines in services/*/ (pins/ split into 6 modules)
- [x] All generators still work
- [x] All tests pass (197 passed)
- [x] Import paths documented (CODEGEN.md, ADDING_COMMANDS.md, EXTENDING.md updated)
- [x] MARA naming convention applied throughout

---

## References

- [CODEGEN.md](./CODEGEN.md) - Code generation ownership
- [COMPOSITION.md](./COMPOSITION.md) - Architecture patterns
- [EXTENDING.md](./EXTENDING.md) - Extension guide
