# Code Generation Ownership

This document defines the canonical sources, generated outputs, and ownership rules for all code generation in the MARA platform.

---

## Golden Rule

> **Never edit generated files. Edit the source, then regenerate.**

---

## Source → Output Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    platform_schema.py (CANONICAL SOURCE)                 │
│                    host/mara_host/tools/platform_schema.py              │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │    generate_all.py      │
                        │                         │
                        │  Runs all generators:   │
                        │  - gen_commands.py      │
                        │  - gen_binary_commands  │
                        │  - gen_telemetry.py     │
                        │  - generate_pins.py     │
                        │  - gpio_mapping_gen.py  │
                        │  - gen_can.py           │
                        └─────────────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               │                                             │
               ▼                                             ▼
┌──────────────────────────────┐           ┌──────────────────────────────┐
│     PYTHON (Host) OUTPUT     │           │      C++ (MCU) OUTPUT        │
├──────────────────────────────┤           ├──────────────────────────────┤
│                              │           │                              │
│  host/mara_host/config/      │           │  firmware/mcu/include/       │
│   ├── command_defs.py        │           │   └── config/                │
│   ├── client_commands.py     │           │       ├── CommandDefs.h      │
│   ├── version.py             │           │       ├── Version.h          │
│   ├── pin_config.py          │           │       ├── PinConfig.h        │
│   └── gpio_channels.py       │           │       ├── GpioChannelDefs.h  │
│                              │           │       └── CanDefs.h          │
│  host/mara_host/command/     │           │                              │
│   ├── binary_commands.py     │           │   └── command/               │
│   └── json_to_binary.py      │           │       └── BinaryCommands.h   │
│                              │           │                              │
│  host/mara_host/telemetry/   │           │   └── telemetry/             │
│   └── telemetry_sections.py  │           │       └── TelemetrySections.h│
│                              │           │                              │
│  host/mara_host/transport/   │           │                              │
│   └── can_defs_generated.py  │           │                              │
│                              │           │                              │
└──────────────────────────────┘           └──────────────────────────────┘
```

---

## Canonical Sources

### platform_schema.py

**Location**: `host/mara_host/tools/platform_schema.py`

**Owns**:
| Section | Description |
|---------|-------------|
| `COMMANDS` | All JSON command definitions |
| `BINARY_COMMANDS` | High-rate binary command specs |
| `TELEMETRY_SECTIONS` | Telemetry section IDs and formats |
| `VERSION` | Firmware/protocol version info |
| `CAPABILITIES` | Device capability flags |
| `GPIO_CHANNELS` | Logical GPIO channel mappings |
| `CAN_*` | CAN bus message definitions |

**Edit this file when**:
- Adding a new command
- Adding a new telemetry section
- Changing protocol version
- Adding capability flags
- Defining CAN messages

### pins.json

**Location**: `host/mara_host/config/pins.json`

**Owns**:
- Physical GPIO pin assignments
- Pin name → GPIO number mapping

**Edit this file when**:
- Changing hardware pin assignments
- Adding new named pins

---

## Generated Files (DO NOT EDIT)

### Host Python Files

| File | Generator | Content |
|------|-----------|---------|
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
|------|-----------|---------|
| `config/CommandDefs.h` | `gen_commands.py` | `CmdType` enum, string converters |
| `config/Version.h` | `gen_commands.py` | Version namespace with constants |
| `config/PinConfig.h` | `generate_pins.py` | Pin macro definitions |
| `config/GpioChannelDefs.h` | `gpio_mapping_gen.py` | GPIO channel namespace |
| `config/CanDefs.h` | `gen_can.py` | CAN message structs and IDs |
| `command/BinaryCommands.h` | `gen_binary_commands.py` | Binary command opcodes and structs |
| `telemetry/TelemetrySections.h` | `gen_telemetry.py` | Telemetry section IDs |

---

## Regeneration

### Manual Regeneration

```bash
# From repository root
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
- `platform_schema.py`
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

1. **Add schema to `platform_schema.py`**
   ```python
   NEW_THING = {
       "item1": {...},
       "item2": {...},
   }
   ```

2. **Create generator in `host/mara_host/tools/`**
   ```python
   # gen_new_thing.py
   from platform_schema import NEW_THING, PY_CONFIG_DIR, CPP_CONFIG_DIR

   def generate_python(): ...
   def generate_cpp(): ...
   def main(): ...
   ```

3. **Register in `generate_all.py`**
   ```python
   import gen_new_thing
   # ... in main():
   gen_new_thing.main()
   ```

4. **Add CLI command** (optional)
   ```python
   # cli/commands/generate.py
   def cmd_new_thing(args):
       gen_new_thing.main()
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

Check that `platform_schema.py` is valid Python:
```bash
cd host/mara_host/tools
python -c "import platform_schema; print('OK')"
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
|--------|-------|-------------------|
| `platform_schema.py` | Yes | Yes |
| `pins.json` | Yes | Yes |
| `config/*.py` | No | - |
| `config/*.h` | No | - |
| `command/binary_commands.py` | No | - |
| `command/BinaryCommands.h` | No | - |
| `telemetry/telemetry_sections.py` | No | - |
| `telemetry/TelemetrySections.h` | No | - |
