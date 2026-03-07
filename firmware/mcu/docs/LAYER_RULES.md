# Firmware Layer Architecture

This document defines the layer dependency rules enforced by `tools/check_layers.py`.

## Layer Hierarchy

```
Tier 5 (Top):     setup/  loop/     - Orchestration, can access everything
                      ↑
Tier 4:           command/  module/ - Command handling, high-level modules
                      ↑
Tier 3:         control/  transport/  telemetry/
                      ↑
Tier 2:           motor/  sensor/  hw/  audio/  - Hardware modules (peers)
                      ↑
Tier 1:              core/          - Core infrastructure
                      ↑
Tier 0:              hal/           - Hardware abstraction
                      ↑
              (platform headers)
```

## Special Layers

### `config/` - Universal Access
Configuration headers (`FeatureFlags.h`, `PinConfig.h`, etc.) can be included
by **any layer**. They contain compile-time constants only, no runtime logic.

### Composition Roots
These files are allowed to break layer rules because they wire everything together:
- `core/ServiceStorage.h` / `.cpp`
- `core/Runtime.h` / `.cpp`
- `core/McuHost.cpp`

## Dependency Rules

| Layer | Can Include | Cannot Include |
|-------|-------------|----------------|
| `hal/` | platform headers, `config/` | everything else |
| `core/` | `hal/`, `config/` | `motor/`, `sensor/`, `control/`, higher |
| `motor/` | `hal/`, `core/`, `config/`, `control/` | `sensor/`, `transport/`, `command/`, higher |
| `sensor/` | `hal/`, `core/`, `config/`, `control/` | `motor/`, `transport/`, `command/`, higher |
| `transport/` | `hal/`, `core/`, `config/` | `motor/`, `sensor/`, `control/`, higher |
| `control/` | `hal/`, `core/`, `motor/`, `sensor/`, `config/` | `transport/`, `command/`, higher |
| `telemetry/` | `hal/`, `core/`, `motor/`, `sensor/`, `control/`, `config/` | `command/`, higher |
| `command/` | most layers | `setup/`, `loop/` |
| `module/` | most layers | `setup/`, `loop/` |
| `setup/`, `loop/` | everything | - |

## Key Constraints

1. **motor/ and sensor/ are peers** - They should not include each other.
   If you need shared types, put them in `core/`.

2. **transport/ is domain-agnostic** - It handles bytes, not robot concepts.
   No includes from `motor/`, `sensor/`, or `control/`.

3. **hal/ is platform-only** - Only platform SDK headers and `config/`.

4. **control/ can use actuators and sensors** - But not command handling.

## Running the Check

```bash
# From repo root
make check-layers

# Or directly
cd firmware/mcu && python3 tools/check_layers.py
```

## Adding New Layers

1. Add to `ALL_LAYERS` in `tools/check_layers.py`
2. Add rules to `FORBIDDEN_INCLUDES`
3. Document in this file
