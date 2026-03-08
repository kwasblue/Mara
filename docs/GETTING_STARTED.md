# Getting Started with MARA

<div align="center">

**Build your first robot with MARA**

*From hardware setup to autonomous control*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## What is MARA?

MARA (Modular Asynchronous Robotics Architecture) is a platform for building ESP32-based robots.

| Component | What it does |
|:----------|:-------------|
| **ESP32 Firmware** | Real-time motor control, sensor reading, safety |
| **Python Host** | High-level control, telemetry, research tools |
| **CLI (`mara`)** | Testing, calibration, monitoring |

---

## Step 1: Hardware Requirements

### Minimum Setup

| Part | Purpose | Example |
|:-----|:--------|:--------|
| ESP32 dev board | Main controller | ESP32-DevKitC, ESP32-S3 |
| USB cable | Programming & serial | Micro-USB or USB-C |
| DC motors (2x) | Drive wheels | TT motors, N20 motors |
| Motor driver | PWM control | L298N, TB6612, DRV8833 |
| Power supply | Motors & ESP32 | 7.4V LiPo + 5V regulator |

### Wiring Example

```
ESP32                    Motor Driver (L298N)
─────                    ────────────────────
GPIO 25 (PWM) ──────────► ENA (Left motor enable)
GPIO 26 ────────────────► IN1 (Left forward)
GPIO 27 ────────────────► IN2 (Left reverse)

GPIO 14 (PWM) ──────────► ENB (Right motor enable)
GPIO 12 ────────────────► IN3 (Right forward)
GPIO 13 ────────────────► IN4 (Right reverse)

GND ────────────────────► GND
```

---

## Step 2: Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/mara.git
cd mara
```

### Install Python Host

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install MARA
pip install -e host/
```

### Install PlatformIO (for firmware)

```bash
pip install platformio
```

---

## Step 3: Configure Your Robot

### Pin Configuration

Edit `host/mara_host/config/pins.json`:

```json
{
  "motors": {
    "left": {
      "pwm": 25,
      "in1": 26,
      "in2": 27
    },
    "right": {
      "pwm": 14,
      "in1": 12,
      "in2": 13
    }
  },
  "encoders": {
    "left": {"a": 34, "b": 35},
    "right": {"a": 32, "b": 33}
  }
}
```

### Generate Configuration

```bash
mara generate pins
```

---

## Step 4: Build & Flash Firmware

### Choose Build Profile

| Profile | Features | Use case |
|:--------|:---------|:---------|
| `esp32_minimal` | UART only | Debugging |
| `esp32_motors` | Motors + encoders | Basic robot |
| `esp32_full` | Everything | Development |

### Build and Flash

```bash
cd firmware/mcu

# Build
pio run -e esp32_motors

# Flash (connect ESP32 via USB)
pio run -e esp32_motors -t upload

# Monitor serial output
pio device monitor -b 115200
```

Expected output:
```
[MCU] Booting...
[MOTORS] Initialized 2 DC motors
[SAFETY] ModeManager started
```

---

## Step 5: First Connection

### Find Serial Port

```bash
# macOS
ls /dev/cu.usbserial-*

# Linux
ls /dev/ttyUSB*
```

### Test Connection

```bash
mara test connection --port /dev/cu.usbserial-0001
```

Expected:
```
✓ Serial port opened
✓ Handshake successful
✓ Firmware version: 1.0.0
✓ Protocol version: 1
```

---

## Step 6: Your First Program

### Basic Motor Control

```python
# my_robot.py
import asyncio
from mara_host import Robot

async def main():
    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Safety sequence
        await robot.arm()
        await robot.activate()

        # Drive forward for 2 seconds
        await robot.motion.set_velocity(vx=0.3, omega=0.0)
        await asyncio.sleep(2.0)

        # Stop
        await robot.motion.stop()

        # Cleanup
        await robot.deactivate()
        await robot.disarm()

asyncio.run(main())
```

Run it:
```bash
python my_robot.py
```

---

## Step 7: High-Level API

For more complex behaviors:

```python
import asyncio
from mara_host import Robot
from mara_host.api import GPIO

async def main():
    async with Robot("/dev/cu.usbserial-0001") as robot:
        gpio = GPIO(robot)

        # Setup LED on channel 0
        await gpio.register(channel=0, pin=2, mode="output")

        await robot.arm()
        await robot.activate()

        # Blink while driving
        for _ in range(4):
            await gpio.high(0)
            await robot.motion.set_velocity(0.3, 0.0, binary=True)
            await asyncio.sleep(0.5)

            await gpio.low(0)
            await robot.motion.set_velocity(0.0, 0.3, binary=True)
            await asyncio.sleep(0.5)

        await robot.motion.stop()
        await robot.deactivate()
        await robot.disarm()

asyncio.run(main())
```

---

## Step 8: Telemetry

Subscribe to sensor data:

```python
async def main():
    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Handle IMU data
        @robot.on("telemetry.imu")
        def on_imu(data):
            print(f"Accel: {data['ax']:.2f}, {data['ay']:.2f}")

        # Handle encoder data
        @robot.on("telemetry.encoder0")
        def on_encoder(data):
            print(f"Velocity: {data['velocity']:.2f} rad/s")

        await robot.arm()
        await asyncio.sleep(10)  # Collect data
        await robot.disarm()
```

---

## Step 9: High-Rate Control (50+ Hz)

For real-time control, use binary encoding:

```python
async def control_loop(robot):
    """50Hz control loop with minimal latency."""
    await robot.arm()
    await robot.activate()

    try:
        while True:
            # Get sensor data
            # ... your controller here ...

            # Send velocity (binary for speed)
            await robot.motion.set_velocity(vx, omega, binary=True)
            await asyncio.sleep(0.02)  # 50Hz

    finally:
        await robot.motion.stop()
        await robot.deactivate()
        await robot.disarm()
```

**Performance:**
- JSON path: ~50 bytes, good for setup/config
- Binary path: ~9 bytes, 5x smaller, use for streaming

---

## Step 10: WiFi Connection (Optional)

### Configure WiFi

Edit `firmware/mcu/include/config/WifiSecrets.h`:

```cpp
#define WIFI_STA_SSID        "YourNetwork"
#define WIFI_STA_PASSWORD    "YourPassword"
```

### Flash WiFi Firmware

```bash
pio run -e esp32_usb -t upload
```

### Connect via TCP

```python
from mara_host import Robot

async with Robot("tcp://10.0.0.60:3333") as robot:
    # Same API as serial
    await robot.arm()
    ...
```

---

## Troubleshooting

### "Handshake timed out"

- Check USB cable (some are charge-only)
- Verify correct port: `ls /dev/cu.*`
- Press ESP32 reset button

### "Command rejected: not_armed"

Follow safety sequence:
```python
await robot.arm()       # IDLE → ARMED
await robot.activate()  # ARMED → ACTIVE
# ... do stuff ...
await robot.deactivate()
await robot.disarm()
```

### Motors don't move

1. Check motor driver wiring
2. Verify PWM pins in `pins.json`
3. Test with `mara test motors --port ...`

### WiFi won't connect

1. Check credentials in `WifiSecrets.h`
2. Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
3. Check serial monitor for status

---

## Command Reference

| Command | Description |
|:--------|:------------|
| `mara test connection` | Test serial connection |
| `mara test commands` | Test command ACKs |
| `mara test motors` | Test motor outputs |
| `mara generate all` | Regenerate code |
| `mara calibrate pid` | Tune PID gains |

---

## Next Steps

| Document | Description |
|:---------|:------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [ADDING_COMMANDS.md](ADDING_COMMANDS.md) | Add new commands |
| [EXTENDING.md](EXTENDING.md) | Add sensors, motors |
| [MQTT.md](MQTT.md) | Multi-robot control |

---

<div align="center">

*Need help? Open an issue on GitHub*

</div>
