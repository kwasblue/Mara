# Code Generation

<div align="center">

**Canonical sources, generators, and generated outputs**

*Never edit generated files—edit the source, then regenerate*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Golden Rule

> **Never edit generated files. Edit the source, then regenerate.**

---

## Source to Output Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              mara_host/tools/schema/ (CANONICAL SOURCE PACKAGE)              │
│                                                                              │
│  schema/                                                                     │
│  ├── commands/           # Command definitions by domain                     │
│  │   ├── _safety.py      # Safety/state machine (9 commands)                │
│  │   ├── _rates.py       # Loop rates (4 commands)                          │
│  │   ├── _control.py     # Signal bus, slots (13 commands)                  │
│  │   ├── _motion.py      # Velocity commands (2 commands)                   │
│  │   ├── _gpio.py        # LED, GPIO, PWM (7 commands)                      │
│  │   ├── _servo.py       # Servo (3 commands)                               │
│  │   ├── _stepper.py     # Stepper (3 commands)                             │
│  │   ├── _sensors.py     # Encoder, ultrasonic (5 commands)                 │
│  │   ├── _dc_motor.py    # DC motor + PID (5 commands)                      │
│  │   ├── _observer.py    # Luenberger observer (6 commands)                 │
│  │   ├── _telemetry.py   # Telemetry config (2 commands)                    │
│  │   └── _camera.py      # ESP32-CAM (20 commands)                          │
│  ├── binary.py           # BINARY_COMMANDS                                   │
│  ├── telemetry.py        # TELEMETRY_SECTIONS                                │
│  ├── version.py          # VERSION, CAPABILITIES                             │
│  ├── can.py              # CAN_* definitions                                 │
│  ├── gpio_channels.py    # GPIO_CHANNELS                                     │
│  └── pins.py             # PINS (from pins.json)                             │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
                      ┌─────────────────────────────┐
                      │      generate_all.py        │
                      │                             │
                      │  Runs all generators:       │
                      │  • gen_commands.py          │
                      │  • gen_binary_commands.py   │
                      │  • gen_telemetry.py         │
                      │  • generate_pins.py         │
                      │  • gpio_mapping_gen.py      │
                      │  • gen_can.py               │
                      └─────────────────────────────┘
                                    │
                 ┌──────────────────┴──────────────────┐
                 │                                     │
                 ▼                                     ▼
┌────────────────────────────────┐   ┌────────────────────────────────┐
│      PYTHON (Host) OUTPUT      │   │       C++ (MCU) OUTPUT         │
├────────────────────────────────┤   ├────────────────────────────────┤
│                                │   │                                │
│  host/mara_host/config/        │   │  firmware/mcu/include/         │
│   ├── command_defs.py          │   │   └── config/                  │
│   ├── client_commands.py       │   │       ├── CommandDefs.h        │
│   ├── version.py               │   │       ├── Version.h            │
│   ├── pin_config.py            │   │       ├── PinConfig.h          │
│   └── gpio_channels.py         │   │       ├── GpioChannelDefs.h    │
│                                │   │       └── CanDefs.h            │
│  host/mara_host/command/       │   │                                │
│   ├── binary_commands.py       │   │   └── command/                 │
│   └── json_to_binary.py        │   │       └── BinaryCommands.h     │
│                                │   │                                │
│  host/mara_host/telemetry/     │   │   └── telemetry/               │
│   └── telemetry_sections.py    │   │       └── TelemetrySections.h  │
│                                │   │                                │
│  host/mara_host/transport/     │   │                                │
│   └── can_defs_generated.py    │   │                                │
│                                │   │                                │
└────────────────────────────────┘   └────────────────────────────────┘
```

---

## Canonical Sources

### schema/ Package

**Location**: `host/mara_host/tools/schema/`

The schema package is the single source of truth for all platform definitions. It's organized as a Python package with domain-specific modules.

**Top-level imports**:
```python
from mara_host.tools.schema import COMMANDS, PINS, VERSION
```

### commands/ Subpackage

Commands are organized by domain for maintainability. Each domain file defines a `*_COMMANDS` dict that gets merged into the main `COMMANDS` dict.

| Domain File | Commands | Description |
|:------------|:---------|:------------|
| `_safety.py` | 9 | Identity, heartbeat, arm/disarm, e-stop |
| `_rates.py` | 4 | Loop rate configuration |
| `_control.py` | 13 | Signal bus, slot configuration |
| `_motion.py` | 2 | SET_MODE, SET_VEL |
| `_gpio.py` | 7 | LED, GPIO, PWM |
| `_servo.py` | 3 | Servo commands |
| `_stepper.py` | 3 | Stepper commands |
| `_sensors.py` | 5 | Encoder, ultrasonic |
| `_dc_motor.py` | 5 | DC motor + velocity PID |
| `_observer.py` | 6 | Luenberger state observer |
| `_telemetry.py` | 2 | Telemetry configuration |
| `_camera.py` | 20 | ESP32-CAM over HTTP |

**Edit these files when**:
- Adding a new command (choose appropriate domain)
- Modifying existing command payloads

**Adding a new domain**:
1. Create `_my_domain.py` with `MY_DOMAIN_COMMANDS` dict
2. Register in `__init__.py`: `from ._my_domain import MY_DOMAIN_COMMANDS`
3. Merge into `COMMANDS`: `**MY_DOMAIN_COMMANDS`

### Other Schema Files

| File | Contains | Edit when... |
|:-----|:---------|:-------------|
| `binary.py` | `BINARY_COMMANDS` | Adding high-rate streaming commands |
| `telemetry.py` | `TELEMETRY_SECTIONS` | Adding new telemetry packet types |
| `version.py` | `VERSION`, `CAPABILITIES` | Bumping version, adding capability flags |
| `can.py` | `CAN_*` definitions | Adding CAN bus messages |
| `gpio_channels.py` | `GPIO_CHANNELS` | Adding logical GPIO channels |
| `pins.py` | `PINS` (loads `pins.json`) | - |

### pins.json

**Location**: `host/mara_host/config/pins.json`

**Owns**:
- Physical GPIO pin assignments
- Pin name to GPIO number mapping

**Edit this file when**:
- Changing hardware pin assignments
- Adding new named pins

---

## Generated Files (DO NOT EDIT)

### Host Python Files

| File | Generator | Content |
|:-----|:----------|:--------|
| `config/command_defs.py` | `gen_commands.py` | `CommandDef` dataclasses |
| `config/client_commands.py` | `gen_commands.py` | `MaraCommandsMixin` with `cmd_*()` methods |
| `config/version.py` | `gen_commands.py` | Protocol version constants |
| `config/pin_config.py` | `generate_pins.py` | Pin assignment constants |
| `config/gpio_channels.py` | `gpio_mapping_gen.py` | GPIO channel mappings |
| `command/binary_commands.py` | `gen_binary_commands.py` | Binary opcode definitions |
| `command/json_to_binary.py` | `gen_binary_commands.py` | JSON-to-binary encoder |
| `telemetry/telemetry_sections.py` | `gen_telemetry.py` | Section ID constants |
| `transport/can_defs_generated.py` | `gen_can.py` | CAN message definitions |

### MCU C++ Files

| File | Generator | Content |
|:-----|:----------|:--------|
| `config/CommandDefs.h` | `gen_commands.py` | `CmdType` enum, string converters |
| `config/Version.h` | `gen_commands.py` | Version namespace with constants |
| `config/PinConfig.h` | `generate_pins.py` | Pin macro definitions |
| `config/GpioChannelDefs.h` | `gpio_mapping_gen.py` | GPIO channel namespace |
| `config/CanDefs.h` | `gen_can.py` | CAN message structs and IDs |
| `command/BinaryCommands.h` | `gen_binary_commands.py` | Binary command opcodes and structs |
| `telemetry/TelemetrySections.h` | `gen_telemetry.py` | Telemetry section IDs |

---

## Regeneration

### Commands

```bash
# Full regeneration (recommended)
make generate

# Or via CLI
mara generate all

# Or directly
cd host && python -m mara_host.tools.generate_all
```

### Individual Generators

```bash
mara generate commands   # Commands + version
mara generate binary     # Binary commands
mara generate telemetry  # Telemetry sections
mara generate pins       # Pin configuration
mara generate gpio       # GPIO channel mappings
mara generate can        # CAN definitions
```

### When to Regenerate

**Always regenerate after editing**:
- Any file in `schema/commands/`
- `schema/binary.py`
- `schema/telemetry.py`
- `schema/version.py`
- `schema/can.py`
- `schema/gpio_channels.py`
- `pins.json`

**Regenerate before**:
- Building firmware (`make build-mcu`)
- Running tests (`make test`)
- Committing changes

---

## CI Verification

Add to CI pipeline to catch drift:

```bash
#!/bin/bash
# verify-codegen.sh

# Regenerate all artifacts
make generate

# Check for uncommitted changes
if ! git diff --quiet host/mara_host/config/; then
    echo "ERROR: Generated Python files are out of date"
    git diff host/mara_host/config/
    exit 1
fi

if ! git diff --quiet firmware/mcu/include/config/; then
    echo "ERROR: Generated C++ files are out of date"
    git diff firmware/mcu/include/config/
    exit 1
fi

echo "OK: Generated files are up to date"
```

---

## Adding New Generated Artifacts

1. **Add schema to appropriate file in `schema/`**
   ```python
   # For commands: schema/commands/_my_domain.py
   MY_DOMAIN_COMMANDS = {...}

   # For other definitions: schema/my_thing.py
   MY_THING = {...}
   ```

2. **Create generator in `host/mara_host/tools/`**
   ```python
   # gen_my_thing.py
   from mara_host.tools.schema import MY_THING, PY_CONFIG_DIR, CPP_CONFIG_DIR

   def generate_python(): ...
   def generate_cpp(): ...
   def main(): ...
   ```

3. **Register in `generate_all.py`**
   ```python
   import gen_my_thing
   # ... in main():
   gen_my_thing.main()
   ```

4. **Add CLI command** (optional)
   ```python
   # cli/commands/generate.py
   def cmd_my_thing(args):
       gen_my_thing.main()
   ```

5. **Document in this file**

---

## File Headers

All generated files include a header comment:

```python
# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from <source> by <generator>
```

```cpp
// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from <source> by <generator>
```

These headers serve as a clear warning to developers.

---

## Troubleshooting

### "Generated file doesn't match schema"

```bash
make generate
git diff  # See what changed
```

### "Import error in generated file"

Check that schema files are valid Python:
```bash
cd host/mara_host/tools
python -c "from schema import COMMANDS; print(f'{len(COMMANDS)} commands')"
```

### "C++ compile error in generated header"

1. Check generator output:
   ```bash
   mara generate commands
   ```
2. Verify header syntax:
   ```bash
   cd firmware/mcu
   pio run -e native  # Native build catches syntax errors fast
   ```

### "Generator can't find output directory"

Ensure monorepo structure is intact:
```bash
ls firmware/mcu/include/config/  # Should exist
ls host/mara_host/config/        # Should exist
```

---

## Summary

| Source | Edit? | Regenerate After? |
|:-------|:------|:------------------|
| `schema/commands/_*.py` | Yes | Yes |
| `schema/binary.py` | Yes | Yes |
| `schema/telemetry.py` | Yes | Yes |
| `schema/version.py` | Yes | Yes |
| `schema/can.py` | Yes | Yes |
| `schema/gpio_channels.py` | Yes | Yes |
| `pins.json` | Yes | Yes |
| `config/*.py` | No | - |
| `config/*.h` | No | - |
| `command/binary_commands.py` | No | - |
| `command/BinaryCommands.h` | No | - |
| `telemetry/telemetry_sections.py` | No | - |
| `telemetry/TelemetrySections.h` | No | - |

---

<div align="center">

*Single source of truth ensures host and firmware stay in sync*

</div>
