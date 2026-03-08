# ADR-002: Splitting Gravity Well Files

## Status
In Progress (Phase 1 Complete, Phase 6 Partially Complete)

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

```
1. Phase 1: platform_schema.py → schema/ subpackage ✅ COMPLETE
   - Most critical, highest impact
   - Unblocks generator improvements
   - schema/commands/ now has 12 domain files (79 commands total)

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

6. Phase 6: plotting.py, send_all.py ✅ COMPLETE
   - plotting.py → research/plotting/ (9 files, 761 lines)
   - send_all.py → benchmarks/commands/send_all/ (8 files, 1248 lines)
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

- [x] No file > 500 lines in tools/schema/ (commands split to 12 domain files, largest is _camera.py at 423 lines)
- [ ] No file > 300 lines in cli/commands/*/ (test/, run/, calibrate/ already split)
- [ ] No file > 200 lines in services/*/
- [x] All generators still work
- [x] All tests pass (180 passed)
- [x] Import paths documented (CODEGEN.md, ADDING_COMMANDS.md, EXTENDING.md updated)

---

## References

- [CODEGEN.md](./CODEGEN.md) - Code generation ownership
- [COMPOSITION.md](./COMPOSITION.md) - Architecture patterns
- [EXTENDING.md](./EXTENDING.md) - Extension guide
