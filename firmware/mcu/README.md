# MARA Firmware

```
 ███╗   ███╗ █████╗ ██████╗  █████╗
 ████╗ ████║██╔══██╗██╔══██╗██╔══██╗
 ██╔████╔██║███████║██████╔╝███████║
 ██║╚██╔╝██║██╔══██║██╔══██╗██╔══██║
 ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██║
 ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
 Modular Asynchronous Robotics Architecture
```

**ESP32 Firmware Component**

[![PlatformIO](https://img.shields.io/badge/PlatformIO-ESP32-orange)](https://platformio.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Overview

**MARA** (Modular Asynchronous Robotics Architecture) is a complete robotics control framework consisting of:

| Component | Location | Description |
|-----------|----------|-------------|
| **Firmware** | `firmware/mcu/` (this directory) | Real-time motor control, sensor fusion, communication |
| **Host** | `host/mara_host/` | Python async client, telemetry, research tools |
| **CAM Firmware** | `firmware/cam/` | ESP32-CAM streaming and vision |

This repository contains the **ESP32 firmware** - a modular, configurable firmware for ESP32-based robot control systems. Supports differential drive robots, sensors (IMU, encoders, LIDAR, ultrasonic), and multiple communication transports (USB Serial, WiFi, Bluetooth, MQTT).

## Key Features

- **Modular Architecture**: Enable/disable features via compile-time flags
- **Hardware Abstraction Layer (HAL)**: Platform-agnostic interfaces for GPIO, PWM, I2C, Timer, Watchdog - enables porting to STM32, RP2040, and other MCUs
- **Self-Registration**: Add handlers, modules, sensors, transports, and actuators with a single macro
- **Multiple Transports**: USB Serial, WiFi TCP, Bluetooth Classic, MQTT
- **Motor Control**: DC motors, servos, steppers with motion controller
- **Sensors**: IMU (MPU6050), encoders, ultrasonic, LIDAR (VL53L0X)
- **Control System**: Signal bus, PID controllers, state observers
- **Telemetry**: Binary and JSON telemetry streaming at 50+ Hz
- **Safety**: E-STOP, watchdog, connection monitoring

## Quick Start

### Prerequisites

- [PlatformIO](https://platformio.org/) (VS Code extension or CLI)
- ESP32 development board (ESP32-DevKitC, ESP32-S3, etc.)
- USB cable for programming

### Build & Upload

```bash
# Build the full firmware
pio run -e esp32_usb

# Upload to ESP32
pio run -e esp32_usb -t upload

# Monitor serial output
pio device monitor -b 115200
```

### Build Profiles

| Profile | Description | Flash Size |
|---------|-------------|------------|
| `esp32_minimal` | UART only, bare minimum | ~350KB |
| `esp32_motors` | Motors + encoders, no network | ~550KB |
| `esp32_sensors` | WiFi + all sensors, no motors | ~600KB |
| `esp32_control` | Full control system | ~750KB |
| `esp32_full` | Everything enabled | ~870KB |
| `esp32_usb` | Full + USB upload (default) | ~870KB |
| `esp32_ota` | Full + OTA upload | ~870KB |

### WiFi & MQTT Configuration

For WiFi-enabled builds, configure your network credentials:

```bash
# Edit the secrets file (gitignored)
nano include/config/WifiSecrets.h
```

```cpp
// WiFi credentials
#define WIFI_STA_SSID        "YourNetworkName"
#define WIFI_STA_PASSWORD    "YourPassword"

// MQTT broker (for fleet control)
#define MQTT_BROKER_HOST     "10.0.0.59"  // Your host machine IP
#define MQTT_BROKER_PORT     1883
#define MQTT_ROBOT_ID        "mara_bot"
```

Start the MQTT broker on your host:
```bash
mara mqtt start
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.cpp                                 │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│  Transport  │   Command   │   Control   │   Module    │   HW    │
│  Layer      │   Layer     │   Layer     │   Layer     │  Layer  │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────┤
│ UartTrans   │ CmdHandler  │ SignalBus   │ Telemetry   │ GPIO    │
│ WifiTrans   │ MsgRouter   │ CtrlKernel  │ Heartbeat   │ PWM     │
│ BleTrans    │ ModeManager │ Observer    │ Identity    │ Safety  │
│ MqttTrans   │             │ PID         │ Logging     │         │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────┤
│                         EventBus                                 │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│ DcMotor     │ Servo       │ IMU         │ Encoder     │ Lidar   │
│ Manager     │ Manager     │ Manager     │ Manager     │ Manager │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────┤
│                  Hardware Abstraction Layer (HAL)                │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│   IGpio     │    IPwm     │    II2c     │   ITimer    │IWatchdog│
│  (GPIO)     │   (PWM)     │   (I2C)     │  (Timers)   │ (WDT)   │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────┤
│              Platform Implementation (esp32/, stm32/, rp2040/)   │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
firmware/mcu/
├── include/
│   ├── config/          # Build configuration
│   │   ├── FeatureFlags.h   # Feature flag definitions
│   │   ├── PinConfig.h      # Pin assignments
│   │   └── LoopRates.h      # Timing configuration
│   ├── core/            # Core interfaces
│   │   ├── Event.h          # Event system
│   │   ├── EventBus.h       # Pub/sub messaging
│   │   ├── IModule.h        # Module interface
│   │   ├── ModuleManager.h  # Module registry (extensible)
│   │   ├── ModuleMacros.h   # REGISTER_MODULE macro
│   │   └── Protocol.h       # Frame protocol
│   ├── transport/       # Communication transports
│   │   ├── IRegisteredTransport.h  # Self-registration interface
│   │   ├── TransportRegistry.h     # Transport registry
│   │   ├── UartTransport.h
│   │   ├── WifiTransport.h
│   │   ├── BleTransport.h
│   │   └── MqttTransport.h
│   ├── motor/           # Motor drivers + actuators
│   │   ├── IActuator.h         # Self-registration interface
│   │   ├── ActuatorRegistry.h  # Actuator registry
│   │   ├── DcMotorActuator.h   # Self-registering DC motor
│   │   ├── DcMotorManager.h
│   │   ├── ServoManager.h
│   │   ├── StepperManager.h
│   │   └── MotionController.h
│   ├── sensor/          # Sensor interfaces
│   │   ├── ISensor.h           # Self-registration interface
│   │   ├── SensorRegistry.h    # Sensor registry
│   │   ├── ImuManager.h
│   │   ├── EncoderManager.h
│   │   ├── UltrasonicManager.h
│   │   └── LidarManager.h
│   ├── control/         # Control system
│   │   ├── SignalBus.h      # Signal routing
│   │   ├── ControlKernel.h  # Control loop
│   │   └── Observer.h       # State estimation
│   ├── command/         # Command handling
│   │   ├── CommandRegistry.h   # Legacy dispatcher
│   │   ├── HandlerRegistry.h   # New extensible registry
│   │   ├── IStringHandler.h    # New handler interface
│   │   ├── HandlerMacros.h     # REGISTER_HANDLER macro
│   │   ├── MessageRouter.h
│   │   └── ModeManager.h
│   ├── module/          # System modules
│   │   ├── TelemetryModule.h
│   │   ├── HeartbeatModule.h
│   │   └── IdentityModule.h
│   ├── hw/              # Hardware managers (use HAL internally)
│   │   ├── GpioManager.h
│   │   ├── PwmManager.h
│   │   └── SafetyManager.h
│   └── hal/             # Hardware Abstraction Layer
│       ├── Hal.h            # Unified HAL header + HalContext
│       ├── IGpio.h          # GPIO interface (pins, interrupts)
│       ├── IPwm.h           # PWM interface (duty, frequency)
│       ├── II2c.h           # I2C interface (read, write)
│       ├── ITimer.h         # Timer interface (delays, callbacks)
│       ├── IWatchdog.h      # Watchdog interface
│       ├── drivers/         # HAL-based device drivers
│       │   └── Vl53l0x.h    # VL53L0X LiDAR (portable)
│       └── esp32/           # ESP32 HAL implementation
│           ├── Esp32Hal.h   # ESP32 HAL storage
│           ├── Esp32Gpio.h/.cpp
│           ├── Esp32Pwm.h/.cpp
│           ├── Esp32I2c.h/.cpp
│           ├── Esp32Timer.h/.cpp
│           └── Esp32Watchdog.h/.cpp
├── src/                 # Implementation files
│   └── (mirrors include structure)
├── test/                # Unit tests
└── platformio.ini       # Build configuration
```

## Configuration

### Feature Flags (`include/config/FeatureFlags.h`)

Enable/disable features at compile time:

```cpp
// Transport
#define HAS_WIFI             1
#define HAS_BLE              0
#define HAS_MQTT_TRANSPORT   0

// Motors
#define HAS_DC_MOTOR         1
#define HAS_SERVO            1
#define HAS_ENCODER          1
#define HAS_MOTION_CONTROLLER 1

// Sensors
#define HAS_IMU              1
#define HAS_LIDAR            0
#define HAS_ULTRASONIC       1

// Control
#define HAS_SIGNAL_BUS       1
#define HAS_CONTROL_KERNEL   1

// System
#define HAS_TELEMETRY        1
#define HAS_HEARTBEAT        1
```

### Pin Configuration (`include/config/PinConfig.h`)

Define hardware pin assignments:

```cpp
// Motor pins
#define MOTOR_L_IN1   25
#define MOTOR_L_IN2   26
#define MOTOR_L_PWM   27
#define MOTOR_R_IN1   32
#define MOTOR_R_IN2   33
#define MOTOR_R_PWM   14

// Encoder pins
#define ENC_L_A       34
#define ENC_L_B       35
#define ENC_R_A       36
#define ENC_R_B       39

// IMU (I2C)
#define IMU_SDA       21
#define IMU_SCL       22
```

## Hardware Abstraction Layer (HAL)

MARA includes a HAL for platform portability. All hardware access goes through abstract interfaces, enabling the firmware to be ported to different MCU platforms.

### Supported Interfaces

| Interface | Purpose | ESP32 Implementation |
|-----------|---------|---------------------|
| `IGpio` | Digital I/O, interrupts | Arduino GPIO + ESP-IDF |
| `IPwm` | PWM output | ESP32 LEDC peripheral |
| `II2c` | I2C communication | Wire library |
| `ITimer` | Timers, delays | esp_timer API |
| `IWatchdog` | Task watchdog | esp_task_wdt API |

### Porting to New Platforms

To port MARA to a new MCU (e.g., STM32, RP2040):

1. Create `include/hal/<platform>/` directory
2. Implement each interface (e.g., `Stm32Gpio : public IGpio`)
3. Create `<Platform>HalStorage` struct with `buildContext()`
4. Update `ServiceStorage.h` to use the new HAL

No changes needed to managers, handlers, or business logic - they all use HAL interfaces.

### HAL-Based Drivers

Some device drivers are implemented using HAL for full portability:

| Driver | Location | Description |
|--------|----------|-------------|
| `Vl53l0x` | `hal/drivers/Vl53l0x.h` | VL53L0X Time-of-Flight sensor |

## Extensibility

MARA uses self-registration patterns to minimize boilerplate when adding components:

| Component | Macro | Files to Edit |
|-----------|-------|---------------|
| Command Handler | `REGISTER_HANDLER(ClassName)` | 1 (+ include) |
| Module | `REGISTER_MODULE(ClassName)` | 1 (+ include) |
| Sensor | `REGISTER_SENSOR(ClassName)` | 1 (+ include) |
| Transport | `REGISTER_TRANSPORT(ClassName)` | 1 (+ include) |
| Actuator | `REGISTER_ACTUATOR(ClassName)` | 1 (+ include) |

Example (adding a new command handler):

```cpp
// include/command/handlers/MyHandler.h
#include "command/IStringHandler.h"
#include "command/HandlerMacros.h"

class MyHandler : public IStringHandler {
public:
    static constexpr const char* CMDS[] = {"CMD_MY_COMMAND", nullptr};
    const char* const* commands() const override { return CMDS; }
    const char* name() const override { return "MyHandler"; }

    void handle(const char* cmd, JsonVariantConst payload, CommandContext& ctx) override {
        // Handle command...
        ctx.sendAck(cmd, true, JsonDocument{});
    }
};

REGISTER_HANDLER(MyHandler);  // Auto-registers at startup
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed extensibility documentation.

## Protocol

MARA uses a binary framing protocol for efficient communication:

```
[HEADER][LEN_HI][LEN_LO][MSG_TYPE][PAYLOAD...][CHECKSUM]
  0xAA     1B      1B       1B       N bytes     1B
```

### Message Types

| Type | Value | Description |
|------|-------|-------------|
| HEARTBEAT | 0x01 | Keep-alive |
| PING | 0x02 | Ping request |
| PONG | 0x03 | Ping response |
| VERSION_REQUEST | 0x04 | Request firmware info |
| VERSION_RESPONSE | 0x05 | Firmware info response |
| TELEMETRY_BIN | 0x30 | Binary telemetry |
| CMD_JSON | 0x50 | JSON command |

### Commands

See `include/docs/commandSets.md` for full command reference.

Common commands:
- `CMD_ARM` / `CMD_DISARM` - Enable/disable motor control
- `CMD_ACTIVATE` / `CMD_DEACTIVATE` - Start/stop motors
- `CMD_SET_VEL` - Set velocity (vx, omega)
- `CMD_ESTOP` / `CMD_CLEAR_ESTOP` - Emergency stop
- `CMD_TELEMETRY_ON` / `CMD_TELEMETRY_OFF` - Enable telemetry

## Testing

```bash
# Run all native unit tests
pio test -e native

# Run specific test
pio test -e native -f test_protocol

# Verbose output
pio test -e native -v
```

## MARA Host Integration

This firmware is designed to work with the MARA Host Python package (`host/mara_host/`):

```python
from mara_host import Robot

async with Robot("/dev/ttyUSB0") as robot:
    await robot.arm()
    await robot.activate()
    await robot.motion.set_velocity(vx=0.2, omega=0.0)
```

### Code Generation

Several headers are auto-generated from `mara_host/tools/platform_schema.py`:

| Generated Header | Schema Source |
|-----------------|---------------|
| `include/config/CommandDefs.h` | `COMMANDS` dict |
| `include/command/BinaryCommands.h` | `BINARY_COMMANDS` dict |
| `include/telemetry/TelemetrySections.h` | `TELEMETRY_SECTIONS` dict |
| `include/config/Version.h` | `VERSION` dict |
| `include/config/PinConfig.h` | `pins.json` |
| `include/config/GpioChannelDefs.h` | `GPIO_CHANNELS` dict |

To regenerate from the repository root:
```bash
make generate
# or
mara generate all
```

## Performance

| Metric | Value |
|--------|-------|
| Control loop rate | 100 Hz |
| Telemetry rate | 50 Hz |
| Command latency | < 5ms |
| Signal lookup | O(1) |

## License

MIT License
