# Adding Commands

<div align="center">

**Complete workflow for adding new commands**

*From schema definition to hardware implementation*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Overview

The build system owns all command definitions through the `mara_host/tools/schema/` package, ensuring consistency between the C++ firmware (ESP32) and Python host.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            COMMAND FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Define in Schema       →  2. Generate Code      →  3. Implement Handler │
│     tools/schema/commands/     mara generate all        firmware/mcu/       │
│                                                                             │
│  ┌───────────────────┐      ┌──────────────────┐      ┌──────────────────┐ │
│  │ _motion.py        │  →   │ CommandDefs.h    │  →   │ MotionHandler.h  │ │
│  │ CMD_SET_VEL: {...}│      │ command_defs.py  │      │ handle(...)      │ │
│  └───────────────────┘      │ client_commands.py│     └──────────────────┘ │
│                             └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Build World Owns

| Data | Schema Location | C++ Output | Python Output |
|:-----|:----------------|:-----------|:--------------|
| Commands | `schema/commands/` | `CommandDefs.h` | `command_defs.py`, `client_commands.py` |
| Binary Commands | `schema/binary.py` | `BinaryCommands.h` | `binary_commands.py`, `json_to_binary.py` |
| Telemetry Sections | `schema/telemetry.py` | `TelemetrySections.h` | `telemetry_sections.py` |
| Version | `schema/version.py` | `Version.h` | `version.py` |
| Pins | `pins.json` | `PinConfig.h` | `pin_config.py` |
| GPIO Channels | `schema/gpio_channels.py` | `GpioChannelDefs.h` | `gpio_channels.py` |

---

## Schema Structure

Commands are organized by domain in `mara_host/tools/schema/commands/`:

```
schema/commands/
├── __init__.py         # Merges all domains into COMMANDS dict
├── _safety.py          # Safety/state machine (9 commands)
├── _rates.py           # Loop rate configuration (4 commands)
├── _control.py         # Signal bus, slots (13 commands)
├── _motion.py          # SET_MODE, SET_VEL (2 commands)
├── _gpio.py            # LED, GPIO, PWM (7 commands)
├── _servo.py           # Servo commands (3 commands)
├── _stepper.py         # Stepper commands (3 commands)
├── _sensors.py         # Ultrasonic, encoder (5 commands)
├── _dc_motor.py        # DC motor + PID (5 commands)
├── _observer.py        # Luenberger observer (6 commands)
├── _telemetry.py       # Telemetry config (2 commands)
└── _camera.py          # ESP32-CAM over HTTP (20 commands)
```

---

## Step 1: Define Command in Schema

Choose the appropriate domain file and add your command.

### For JSON Commands (setup/config)

**Example: Adding a new sensor command**

Edit `mara_host/tools/schema/commands/_sensors.py`:

```python
# In SENSOR_COMMANDS dict
"CMD_MY_NEW_SENSOR": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "Description of what this command does.",
    "payload": {
        "sensor_id": {"type": "int", "required": True, "description": "..."},
        "threshold": {"type": "float", "required": False, "default": 0.0},
    },
},
```

### Adding a New Domain

If your commands don't fit existing domains, create a new module:

```python
# mara_host/tools/schema/commands/_my_domain.py
"""My domain command definitions."""

MY_DOMAIN_COMMANDS: dict[str, dict] = {
    "CMD_MY_COMMAND": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "...",
        "payload": {...},
    },
}
```

Then register in `__init__.py`:

```python
# mara_host/tools/schema/commands/__init__.py
from ._my_domain import MY_DOMAIN_COMMANDS

COMMANDS: dict[str, dict] = {
    # ... existing domains ...
    **MY_DOMAIN_COMMANDS,
}

__all__ = [
    "COMMANDS",
    # ... existing exports ...
    "MY_DOMAIN_COMMANDS",
]
```

### For Binary Commands (high-rate streaming)

Add to the appropriate domain file, then add encoding spec in `schema/binary.py`:

```python
# In schema/binary.py - BINARY_COMMANDS dict
"MY_BINARY_CMD": {
    "opcode": 0x22,  # Pick next available opcode
    "json_cmd": "CMD_MY_BINARY_CMD",  # Links to JSON command
    "description": "High-rate streaming command.",
    "payload": [
        {"name": "value", "type": "f32"},
    ],
},
```

### Opcode Ranges (Convention)

| Range | Purpose |
|:------|:--------|
| `0x10-0x1F` | Motion/velocity commands |
| `0x20-0x2F` | Safety/heartbeat commands |
| `0x30-0x3F` | Sensor commands |
| `0x40+` | Future expansion |

### Type Mappings

| Schema Type | C++ Type | Python Type | Struct Format |
|:------------|:---------|:------------|:--------------|
| `int` | `int` | `int` | - |
| `float` | `float` | `float` | - |
| `string` | `const char*` | `str` | - |
| `bool` | `bool` | `bool` | - |
| `u8` | `uint8_t` | `int` | `B` |
| `u16` | `uint16_t` | `int` | `H` |
| `u32` | `uint32_t` | `int` | `I` |
| `f32` | `float` | `float` | `f` |

---

## Step 2: Run Generators

```bash
cd /path/to/Host
source .venv/bin/activate
mara generate all
```

This generates:
- `CommandDefs.h` - C++ enum with new command
- `command_defs.py` - Python constant
- `client_commands.py` - Python async method `cmd_my_new_command()`
- `BinaryCommands.h` - C++ opcode, struct, decode (if binary)
- `binary_commands.py` - Python Opcode, encoder (if binary)
- `json_to_binary.py` - JSON to binary mapping (if binary)

---

## Step 3: Implement Handler (MCU C++)

### Choose the Appropriate Handler

| Domain | Handler File | Location |
|:-------|:-------------|:---------|
| Safety/Mode | `SafetyHandler.h` | `include/command/handlers/` |
| Motion/Velocity | `MotionHandler.h` | `include/command/handlers/` |
| GPIO/PWM | `GpioHandler.h` | `include/command/handlers/` |
| Servo | `ServoHandler.h` | `include/command/handlers/` |
| Stepper | `StepperHandler.h` | `include/command/handlers/` |
| DC Motor | `DcMotorHandler.h` | `include/command/handlers/` |
| Sensors | `SensorHandler.h` | `include/command/handlers/` |
| Telemetry | `TelemetryHandler.h` | `include/command/handlers/` |
| Control Kernel | `ControlHandler.h` | `include/command/handlers/` |
| Observer | `ObserverHandler.h` | `include/command/handlers/` |

### Add to Handler

```cpp
// In handler .h file

// 1. Add to command list
const char* handledCommands() const override {
    return "CMD_EXISTING,CMD_MY_NEW_COMMAND";  // Add here
}

// 2. Implement handler
void handle(const JsonDocument& doc, CommandContext& ctx) override {
    const char* type = doc["type"];

    if (strcmp(type, "CMD_MY_NEW_COMMAND") == 0) {
        int param1 = doc["param1"] | 0;
        float param2 = doc["param2"] | 0.0f;

        // Do the work...

        ctx.ack(type, "ok");  // Send ACK
        return;
    }
    // ... existing commands
}
```

---

## Step 4: Build & Test

### Run All Tests

```bash
# From repository root
cd /path/to/mara

# 1. Run all tests (MCU + Host)
make test

# 2. MCU Native Tests only
make test-mcu

# 3. Python Host Tests only
make test-host

# 4. Flash firmware for HIL tests
make flash-mcu

# 5. HIL Tests
make test-hil
```

### Test Coverage

| Test Suite | Command | Tests | What It Verifies |
|:-----------|:--------|:------|:-----------------|
| Native | `pio test -e native` | 37 | Protocol, EventBus, Safety, Handlers |
| ESP32 On-Device | `pio test -e esp32_test` | 31 | Same tests on actual ESP32 |
| Python Host | `pytest tests/` | 80+ | Client, encoders, protocol |
| HIL | `pytest --run-hil` | 46 | Full system over TCP to real ESP32 |

---

## Step 5: Add Service Method (Optional)

For commonly used commands, add a service method:

```python
# services/control/my_service.py
from mara_host.core.result import ServiceResult

class MyService:
    async def my_operation(self, param: int) -> ServiceResult:
        """Perform my operation."""
        ok, error = await self.client.send_reliable(
            "CMD_MY_NEW_COMMAND",
            {"param1": param, "param2": 3.14},
        )

        if ok:
            return ServiceResult.success(data={"param": param})
        else:
            return ServiceResult.failure(error=error or "Failed")
```

---

## Step 6: Add Tests

### Python HIL Test

Edit `tests/test_hil_send_commands.py`:

```python
class TestMyFeature:
    async def test_my_new_command(self, hil):
        ack = await hil.assert_ok("CMD_MY_NEW_COMMAND", {
            "param1": 42,
            "param2": 3.14
        })
        assert ack["status"] == "ok"
```

### MCU Native Test (Optional)

Edit `test/test_command_handler_ack/test_command_handler_ack.cpp`:

```cpp
void test_my_new_command() {
    int startCount = txCount;

    injectJson(R"({
        "kind":"cmd",
        "type":"CMD_MY_NEW_COMMAND",
        "seq":500,
        "param1":42
    })");

    TEST_ASSERT_EQUAL(startCount + 1, txCount);
    TEST_ASSERT_TRUE(lastTx.find("CMD_MY_NEW_COMMAND") != std::string::npos);
}

// Add to run_tests():
RUN_TEST(test_my_new_command);
```

---

## Step 7: Use from Python Host

```python
# Using generated client method (via commander)
await client.cmd_my_new_command(param1=42, param2=3.14)

# Using service method
result = await my_service.my_operation(param=42)
if result.ok:
    print(f"Success: {result.data}")

# For binary streaming (high-rate, goes through commander)
await client.send_stream(
    "CMD_SET_VEL",
    {"vx": 0.5, "omega": 0.0},
    binary=True,  # Uses binary encoding
)
```

---

## Quick Reference

### Adding a JSON Command (Setup/Config)

1. Add to appropriate domain file in `schema/commands/`
2. Run `mara generate all`
3. Implement handler in appropriate `*Handler.h`
4. Run tests: `pio test -e native && pytest tests/`
5. Flash and run HIL: `pio run -t upload && pytest --run-hil`

### Adding a Binary Command (High-Rate Streaming)

1. Add JSON definition to `schema/commands/` (appropriate domain file)
2. Add binary spec to `schema/binary.py`
3. Run `mara generate all`
4. Implement handler (receives via `onBinaryCommand`)
5. Run all tests

### Adding a Telemetry Section

1. Add to `TELEMETRY_SECTIONS` in `schema/telemetry.py`
2. Run `mara generate all`
3. Add parser in `binary_parser.py` using the generated section ID constant
4. Add model in `telemetry/models.py` if needed

---

## Command Domain Quick Reference

| Domain | File | Example Commands |
|:-------|:-----|:-----------------|
| Safety | `_safety.py` | `CMD_IDENTITY`, `CMD_ARM`, `CMD_ESTOP` |
| Rates | `_rates.py` | `CMD_CTRL_SET_RATE`, `CMD_GET_RATES` |
| Control | `_control.py` | `CMD_SIGNAL_DEFINE`, `CMD_SLOT_*` |
| Motion | `_motion.py` | `CMD_SET_MODE`, `CMD_SET_VEL` |
| GPIO | `_gpio.py` | `CMD_LED_SET`, `CMD_PWM_SET` |
| Servo | `_servo.py` | `CMD_SERVO_ATTACH`, `CMD_SERVO_SET` |
| Stepper | `_stepper.py` | `CMD_STEPPER_*` |
| Sensors | `_sensors.py` | `CMD_ENCODER_*`, `CMD_ULTRASONIC_*` |
| DC Motor | `_dc_motor.py` | `CMD_DC_SET_SPEED`, `CMD_DC_VEL_PID_*` |
| Observer | `_observer.py` | `CMD_OBSERVER_CONFIG`, `CMD_OBSERVER_*` |
| Telemetry | `_telemetry.py` | `CMD_TELEM_SET_INTERVAL` |
| Camera | `_camera.py` | `CMD_CAM_*` |

---

## File Locations

| File | Purpose |
|:-----|:--------|
| `host/mara_host/tools/schema/` | Single source of truth (package) |
| `host/mara_host/tools/schema/commands/` | Command definitions by domain |
| `host/mara_host/tools/generate_all.py` | Run all generators |
| `host/mara_host/services/control/` | Service layer with business logic |
| `firmware/mcu/include/command/handlers/` | Command handlers |
| `host/tests/test_hil_send_commands.py` | HIL tests |

---

<div align="center">

*All commands flow through ReliableCommander for consistent event emission and metrics*

</div>
