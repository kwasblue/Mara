# Adding Commands - Complete Workflow

## Overview

This document describes how to add new commands to the robot platform. The build system owns all command definitions through the `mara_host/tools/schema/` package, ensuring consistency between the C++ firmware (ESP32) and Python host.

---

## What Build World Owns

| Data | Schema Location | C++ Output | Python Output |
|------|-----------------|------------|---------------|
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

Add to the appropriate domain file in `commands/`, then add encoding spec in `schema/binary.py`:

```python
# In appropriate domain file (e.g., _motion.py)
"CMD_MY_BINARY_CMD": {
    "kind": "cmd",
    "direction": "host->mcu",
    "description": "High-rate streaming command.",
    "payload": {
        "value": {"type": "float", "required": True},
    },
},
```

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
|-------|---------|
| `0x10-0x1F` | Motion/velocity commands |
| `0x20-0x2F` | Safety/heartbeat commands |
| `0x30-0x3F` | Sensor commands |
| `0x40+` | Future expansion |

### Type Mappings

| Schema Type | C++ Type | Python Type | Struct Format |
|-------------|----------|-------------|---------------|
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
python mara_host/tools/generate_all.py
```

This generates:
- `CommandDefs.h` - C++ enum with new command
- `command_defs.py` - Python constant
- `client_commands.py` - Python async method `cmd_my_new_command()`
- `BinaryCommands.h` - C++ opcode, struct, decode (if binary)
- `binary_commands.py` - Python Opcode, encoder (if binary)
- `json_to_binary.py` - JSON→binary mapping (if binary)

---

## Step 3: Implement Handler (MCU C++)

### Choose the Appropriate Handler

| Domain | Handler File | Location |
|--------|--------------|----------|
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
# From the repository root
cd /path/to/mara

# 1. Run all tests (MCU + Host)
make test

# 2. MCU Native Tests only
make test-mcu

# 3. Python Host Tests only
make test-host

# 4. Flash firmware for HIL tests
make flash-mcu

# 5. HIL Tests (TCP + serial, with defaults)
make test-hil

# Override defaults if needed
MCU_PORT=/dev/ttyUSB0 ROBOT_HOST=192.168.1.100 make test-hil
```

### Test Coverage

| Test Suite | Command | Tests | What It Verifies |
|------------|---------|-------|------------------|
| Native | `pio test -e native` | 37 | Protocol, EventBus, Safety, Handlers (on Mac) |
| ESP32 On-Device | `pio test -e esp32_test` | 31 | Same tests on actual ESP32 (catches platform bugs) |
| Python Host | `pytest tests/` | 80 | Client, encoders, protocol, control design |
| HIL | `pytest --run-hil` | 46 | Full system over TCP to real ESP32 |

---

## Step 5: Add Tests

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

## Step 6: Test from Python Host

```python
# Using generated client method (recommended)
await client.cmd_my_new_command(param1=42, param2=3.14)

# Or using low-level API
await client.send_json_cmd("CMD_MY_NEW_COMMAND", {
    "param1": 42,
    "param2": 3.14
})

# For binary commands (high-rate)
await client.send_binary({"type": "CMD_MY_BINARY_CMD", "value": 1.5})
```

---

## Cross-Platform Test Runner

Tests use `test/test_runner.h` for cross-platform compatibility:

```cpp
#include "../test_runner.h"

void run_tests() {
    RUN_TEST(test_foo);
    RUN_TEST(test_bar);
}

TEST_RUNNER(run_tests)
```

This macro expands to:
- `main()` on native (Mac/Linux)
- `setup()`/`loop()` on ESP32

---

## Quick Reference

### Adding a JSON Command (Setup/Config)

1. Add to appropriate domain file in `schema/commands/`
2. Run `mara generate all`
3. Implement handler in appropriate `*Handler.h`
4. Run tests: `pio test -e native && pio test -e esp32_test`
5. Flash and run HIL: `pio run -e esp32_usb -t upload && pytest --run-hil`

### Adding a Binary Command (High-Rate Streaming)

1. Add JSON definition to `schema/commands/` (appropriate domain file)
2. Add binary spec to `schema/binary.py`
3. Run `mara generate all`
4. Implement handler (receives via `onBinaryCommand`)
5. Run all tests

### Adding a Telemetry Section

Telemetry sections define the binary format for sensor data sent from MCU to Host.

1. Add to `TELEMETRY_SECTIONS` in `schema/telemetry.py`
2. Run `mara generate all`
3. Add parser in `binary_parser.py` using the generated section ID constant
4. Add model in `telemetry/models.py` if needed

```python
# In schema/telemetry.py - TELEMETRY_SECTIONS dict
"TELEM_MY_SENSOR": {
    "id": 0x07,  # Pick next available ID
    "description": "My sensor data",
    "format": "sensor_id(u8) value(f32) ts_ms(u32)",
    "size": 9,  # Fixed size, or None for variable
},
```

### Command Domain Files

| Domain | File | Example Commands |
|--------|------|------------------|
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

### File Locations

| File | Purpose |
|------|---------|
| `host/mara_host/tools/schema/` | Single source of truth (package) |
| `host/mara_host/tools/schema/commands/` | Command definitions by domain |
| `host/mara_host/tools/generate_all.py` | Run all generators |
| `host/mara_host/control/` | Control design tools (LQR, pole placement) |
| `host/mara_host/telemetry/telemetry_sections.py` | Generated telemetry section IDs |
| `firmware/mcu/include/telemetry/TelemetrySections.h` | Generated C++ section IDs |
| `firmware/mcu/include/command/handlers/` | Command handlers |
| `firmware/mcu/test/test_runner.h` | Cross-platform test macro |
| `host/tests/test_hil_send_commands.py` | HIL tests |

---

## Control System Design Tools

The `mara_host.control` module provides scipy-based tools for designing state-space controllers and observers, with helpers to upload configurations to the MCU.

### Quick Example

```python
import numpy as np
from mara_host.control import (
    StateSpaceModel, lqr, observer_gains, configure_state_feedback
)

# Define system (mass-spring-damper)
A = np.array([[0, 1], [-10, -0.5]])
B = np.array([[0], [1]])
C = np.array([[1, 0]])
model = StateSpaceModel(A, B, C)

# Check system properties
assert model.is_controllable()
assert model.is_observable()

# Design LQR controller
Q = np.diag([100, 1])  # State cost
R = np.array([[1]])    # Control cost
K, S, E = lqr(A, B, Q, R)

# Design observer (5x faster than controller)
obs_poles = [-25, -30]
L = observer_gains(A, C, obs_poles)

# Upload to MCU
signals = {
    "state": [10, 11],      # State estimate signals
    "ref": [12, 13],        # Reference signals
    "control": [20],        # Control output
    "measurement": [30],    # Position measurement
}

result = await configure_state_feedback(
    client, model, K,
    L=L,
    use_observer=True,
    signals=signals,
    controller_rate_hz=100,
    observer_rate_hz=200,
)
```

### Available Functions

| Function | Description |
|----------|-------------|
| `StateSpaceModel(A, B, C, D)` | Create state-space model with validation |
| `lqr(A, B, Q, R)` | Continuous-time LQR gain design |
| `lqr_discrete(A, B, Q, R)` | Discrete-time LQR gain design |
| `pole_placement(A, B, poles)` | Place closed-loop poles |
| `observer_gains(A, C, poles)` | Design observer (Luenberger) gains |
| `lqe(A, C, Q, R)` | Kalman filter gain design |
| `discretize(model, dt, method)` | Discretize continuous-time model |
| `check_stability(A, B, K)` | Verify closed-loop stability |
| `reference_gain(A, B, C, K)` | Compute reference gain Kr |
| `upload_controller(client, config)` | Upload controller to MCU |
| `upload_observer(client, config)` | Upload observer to MCU |
| `configure_state_feedback(...)` | High-level setup helper |

### Run Examples

```bash
python -m mara_host.control.examples
```
