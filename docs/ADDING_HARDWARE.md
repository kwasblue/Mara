# Adding Hardware - End-to-End Guide

This guide walks through adding new hardware (sensors, actuators, peripherals) to the MARA platform.

## Quick Start (2 Files)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ADDING NEW HARDWARE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FILE 1: Hardware Registry (Python)                             │
│          tools/schema/hardware/_sensors.py                      │
│          → Defines commands, telemetry, GUI                     │
│          → Run: mara generate all                               │
│                           ↓                                     │
│  FILE 2: Firmware Driver (C++)                                  │
│          firmware/mcu/include/sensor/MySensor.h                 │
│          → Hardware + command handling in ONE file              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| What | Manual | Auto-Generated |
|------|--------|----------------|
| Hardware definition | ✓ 1 file | - |
| Firmware C++ | ✓ 1 file | - |
| Python commands | - | ✓ `client_commands.py` |
| Python telemetry | - | ✓ `models.py`, `binary_parser.py` |
| GUI blocks | - | ✓ `SENSOR_TYPES`, palette |
| C++ headers | - | ✓ `CommandDefs.h`, `TelemetrySections.h` |

---

## Hardware Registry

The hardware registry (`tools/schema/hardware/`) is the **single source of truth**. Each entry defines:

```python
"sensor_name": {
    "type": "sensor",                    # Type: sensor, actuator, etc.
    "interface": "i2c",                  # Interface: i2c, gpio, uart, spi, adc

    "gui": {                             # Block diagram appearance
        "label": "Display Name",
        "color": "#HEX",
        "outputs": [("port_id", "LABEL")],
        "inputs": [("port_id", "LABEL")],
    },

    "commands": {                        # Host → MCU commands
        "CMD_NAME": {
            "description": "What it does",
            "payload": {
                "param": {"type": "int", "default": 0},
            },
        },
    },

    "telemetry": {                       # MCU → Host data
        "section": "TELEM_NAME",
        "id": 0x08,                      # Unique section ID
        "format": "field(type) ...",     # Binary format
        "size": 4,                       # Bytes (or None for variable)
        "model": {                       # Python dataclass fields
            "name": "TelemetryClassName",
            "fields": [
                ("field_name", "python_type"),
                ("converted", "float", "raw_field * 0.01"),  # With conversion
            ],
        },
    },

    "firmware": {                        # Implementation hints
        "manager": "ManagerClassName",
        "handler": "HandlerName",
        "feature_flag": "HAS_FEATURE",
    },
}
```

---

## Example: Adding a Temperature Sensor

### Step 1: Add to Hardware Registry

Edit `host/mara_host/tools/schema/hardware/_sensors.py`:

```python
SENSOR_HARDWARE: dict[str, dict] = {
    # ... existing sensors ...

    "temp": {
        "type": "sensor",
        "interface": "i2c",

        "gui": {
            "label": "Temperature",
            "color": "#F59E0B",
            "outputs": [("temp", "TEMP")],
        },

        "commands": {
            "CMD_TEMP_ATTACH": {
                "description": "Attach a temperature sensor",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                    "i2c_addr": {"type": "int", "default": 0x48},
                },
            },
            "CMD_TEMP_READ": {
                "description": "Read temperature",
                "payload": {
                    "sensor_id": {"type": "int", "default": 0},
                },
            },
        },

        "telemetry": {
            "section": "TELEM_TEMP",
            "id": 0x08,
            "description": "Temperature reading",
            "format": "sensor_id(u8) ok(u8) temp_centi(i16)",
            "size": 4,
            "model": {
                "name": "TemperatureTelemetry",
                "fields": [
                    ("sensor_id", "int"),
                    ("ok", "bool"),
                    ("temp_c", "float", "temp_centi * 0.01"),
                    ("ts_ms", "int"),
                ],
            },
        },

        "firmware": {
            "manager": "TemperatureManager",
            "handler": "SensorHandler",
            "feature_flag": "HAS_TEMP_SENSOR",
        },
    },
}
```

### Step 2: Run Code Generation

```bash
mara generate all
```

This generates:
- **C++**: `CommandDefs.h` with `CMD_TEMP_ATTACH`, `CMD_TEMP_READ`
- **C++**: `TelemetrySections.h` with `TELEM_TEMP = 0x08`
- **Python**: `client_commands.py` with `cmd_temp_attach()`, `cmd_temp_read()`
- **Python**: Telemetry parser and models
- **GUI**: Temperature sensor appears in block diagram palette

### Step 3: Implement Firmware (ONE FILE)

Create `firmware/mcu/include/sensor/TemperatureSensor.h`:

```cpp
#pragma once
#include "config/FeatureFlags.h"
#include "config/CommandDefs.h"
#include "telemetry/TelemetrySections.h"

#if HAS_TEMP_SENSOR

#include "hal/II2C.h"
#include "command/CommandContext.h"

class TemperatureSensor {
public:
    static constexpr uint8_t MAX_SENSORS = 4;

    struct Sensor {
        uint8_t i2c_addr = 0x48;
        bool attached = false;
        int16_t temp_centi = -27315;  // -273.15°C = invalid
        uint32_t last_read_ms = 0;
    };

    TemperatureSensor(hal::II2C& i2c) : i2c_(i2c) {}

    // ─── Hardware Methods ───────────────────────────────────────
    bool attach(uint8_t id, uint8_t addr) {
        if (id >= MAX_SENSORS) return false;
        sensors_[id].i2c_addr = addr;
        sensors_[id].attached = true;
        return true;
    }

    int16_t read(uint8_t id, uint32_t now_ms) {
        if (id >= MAX_SENSORS || !sensors_[id].attached) return -27315;
        auto& s = sensors_[id];
        if (now_ms - s.last_read_ms < 100) return s.temp_centi;

        uint8_t data[2];
        if (i2c_.readBytes(s.i2c_addr, 0x00, data, 2)) {
            int16_t raw = (data[0] << 4) | (data[1] >> 4);
            if (raw & 0x800) raw |= 0xF000;
            s.temp_centi = raw * 625 / 100;
        }
        s.last_read_ms = now_ms;
        return s.temp_centi;
    }

    // ─── Command Handling ───────────────────────────────────────
    bool canHandle(CmdType cmd) const {
        return cmd == CmdType::TEMP_ATTACH || cmd == CmdType::TEMP_READ;
    }

    void handle(CmdType cmd, JsonVariantConst p, CommandContext& ctx) {
        uint8_t id = p["sensor_id"] | 0;

        if (cmd == CmdType::TEMP_ATTACH) {
            uint8_t addr = p["i2c_addr"] | 0x48;
            attach(id, addr) ? ctx.ack("CMD_TEMP_ATTACH", "ok")
                             : ctx.error("CMD_TEMP_ATTACH", "invalid id");
        }
        else if (cmd == CmdType::TEMP_READ) {
            JsonDocument reply;
            reply["type"] = "CMD_TEMP_READ";
            reply["sensor_id"] = id;
            reply["temp_c"] = read(id, millis()) / 100.0f;
            ctx.reply(reply);
        }
    }

    // ─── Telemetry Publishing ───────────────────────────────────
    void publishTelemetry(BinaryWriter& buf) {
        for (uint8_t id = 0; id < MAX_SENSORS; id++) {
            if (!sensors_[id].attached) continue;
            buf.writeByte(TELEM_TEMP);
            buf.writeU16(4);
            buf.writeByte(id);
            buf.writeByte(1);
            buf.writeI16(sensors_[id].temp_centi);
        }
    }

private:
    hal::II2C& i2c_;
    Sensor sensors_[MAX_SENSORS];
};

#else  // Stub when disabled
class TemperatureSensor {
public:
    TemperatureSensor(hal::II2C&) {}
    bool canHandle(CmdType) const { return false; }
    void handle(CmdType, JsonVariantConst, CommandContext&) {}
    void publishTelemetry(BinaryWriter&) {}
};
#endif
```

Then register in main:
```cpp
TemperatureSensor temp_sensor(i2c);
command_bus.registerHandler(temp_sensor);  // Uses canHandle/handle
telemetry.addProvider([&](auto& buf) { temp_sensor.publishTelemetry(buf); });
```

### Done!

The temperature sensor now:
- Appears in GUI block diagram palette (drag & drop)
- Has Python client methods: `await client.cmd_temp_attach(sensor_id=0)`
- Streams telemetry parsed into `TemperatureTelemetry` dataclass

---

## Checklist

### Required (3 files + codegen)
- [ ] Add entry to `tools/schema/hardware/_sensors.py`
- [ ] Run `mara generate all`
- [ ] Create `firmware/mcu/include/sensor/MyManager.h`
- [ ] Add handler cases in `firmware/mcu/include/command/handlers/`

### Optional
- [ ] Add feature flag in `FeatureFlags.h`
- [ ] Create dedicated Python service in `services/control/`
- [ ] Add HIL test in `tests/test_hil_send_commands.py`
- [ ] Add MCU native test in `firmware/mcu/test/`

---

## File Reference

### You Edit (3 files)
| File | Purpose |
|------|---------|
| `tools/schema/hardware/_sensors.py` | Hardware definition |
| `firmware/mcu/include/sensor/*.h` | Hardware driver |
| `firmware/mcu/include/command/handlers/*.h` | Command handler |

### Auto-Generated (don't edit)
| File | Source |
|------|--------|
| `CommandDefs.h` | Hardware registry |
| `TelemetrySections.h` | Hardware registry |
| `command_defs.py` | Hardware registry |
| `client_commands.py` | Hardware registry |
| `telemetry_sections.py` | Hardware registry |
| GUI `SENSOR_TYPES` | Hardware registry (runtime) |

---

## Format Reference

### Telemetry Format String

| Type | Bytes | C++ | Python |
|------|-------|-----|--------|
| `u8` | 1 | `uint8_t` | `int` |
| `i8` | 1 | `int8_t` | `int` |
| `u16` | 2 | `uint16_t` | `int` |
| `i16` | 2 | `int16_t` | `int` |
| `u32` | 4 | `uint32_t` | `int` |
| `i32` | 4 | `int32_t` | `int` |
| `f32` | 4 | `float` | `float` |

Example: `"sensor_id(u8) ok(u8) value(i16)"` = 4 bytes total

### Interface Types

| Interface | Typical Ports | Use Case |
|-----------|---------------|----------|
| `i2c` | SDA, SCL | IMU, temperature, OLED |
| `gpio` | TRIG, ECHO, A, B | Ultrasonic, encoder |
| `uart` | TX, RX | LiDAR, GPS |
| `spi` | MOSI, MISO, SCK, CS | Display, SD card |
| `adc` | OUT | IR sensor, potentiometer |

---

## Tips

1. **Use feature flags** - Wrap C++ in `#if HAS_FEATURE` so unused hardware compiles out
2. **Non-blocking reads** - Cache values in managers; never block the main loop
3. **Fixed telemetry sizes** - Use fixed-size sections when possible for efficient parsing
4. **Rate limit** - Don't read sensors faster than they update (waste of I2C bandwidth)
5. **Test incrementally** - Test firmware with native tests before HIL

See also: [ADDING_COMMANDS.md](./ADDING_COMMANDS.md) for command schema details.
