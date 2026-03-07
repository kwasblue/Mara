# Getting Started with MARA

This guide walks you through building a robot with the MARA platform, from hardware setup to your first autonomous program.

---

## Overview

MARA (Modular Asynchronous Robotics Architecture) consists of:

| Component | What it does |
|-----------|--------------|
| **ESP32 Firmware** | Real-time motor control, sensor reading, safety |
| **Python Host** | High-level control, telemetry, research tools |
| **CLI (`mara`)** | Testing, calibration, monitoring |

---

## Step 1: Hardware Requirements

### Minimum Setup

| Part | Purpose | Example |
|------|---------|---------|
| ESP32 dev board | Main controller | ESP32-DevKitC, ESP32-S3 |
| USB cable | Programming & serial | Micro-USB or USB-C |
| DC motors (2x) | Drive wheels | TT motors, N20 motors |
| Motor driver | PWM control | L298N, TB6612, DRV8833 |
| Encoders (optional) | Velocity feedback | Hall effect or optical |
| Power supply | Motors & ESP32 | 7.4V LiPo + 5V regulator |

### Wiring Example (Differential Drive)

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

## Step 2: Install the Platform

### Clone the Repository

```bash
git clone https://github.com/yourusername/mara.git
cd mara
```

### Install Python Host

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install MARA
make install
```

### Install PlatformIO (for firmware)

```bash
pip install platformio
```

---

## Step 3: Configure Your Robot

### Pin Configuration

Edit `host/mara_host/config/pins.json` with your GPIO assignments:

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

This creates matching Python and C++ config files.

---

## Step 4: Build & Flash Firmware

### Choose a Build Profile

| Profile | Features | Use case |
|---------|----------|----------|
| `esp32_minimal` | UART only | Debugging |
| `esp32_motors` | Motors + encoders | Basic robot |
| `esp32_control` | Full control system | Advanced |
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

You should see:
```
[MCU] Booting...
[MOTORS] Initialized 2 DC motors
[SAFETY] ModeManager started
```

---

## Step 5: First Connection

### Find Your Serial Port

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

Expected output:
```
✓ Serial port opened
✓ Handshake successful
✓ Firmware version: 1.0.0
✓ Protocol version: 1
```

### Run Hardware Tests

```bash
mara test commands --port /dev/cu.usbserial-0001
```

---

## Step 6: Your First Program

### Basic Motor Control

```python
# my_robot.py
import asyncio
from mara_host.transport.serial_transport import SerialTransport
from mara_host.command.client import MaraClient

async def main():
    # Connect
    transport = SerialTransport("/dev/cu.usbserial-0001")
    client = MaraClient(transport)

    await client.start()

    try:
        # Safety sequence: arm → activate
        await client.cmd_arm()
        await client.cmd_activate()

        # Drive forward for 2 seconds
        await client.set_vel(vx=0.3, omega=0.0)
        await asyncio.sleep(2.0)

        # Stop
        await client.cmd_stop()

    finally:
        # Always cleanup
        await client.cmd_deactivate()
        await client.cmd_disarm()
        await client.stop()

asyncio.run(main())
```

Run it:
```bash
python my_robot.py
```

---

## Step 7: Using the High-Level API

For more complex behaviors, use the API layer:

```python
import asyncio
from mara_host import Robot, DifferentialDrive, GPIO

async def main():
    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Create high-level interfaces
        drive = DifferentialDrive(robot)
        gpio = GPIO(robot)

        # Setup an LED
        await gpio.register(channel=0, pin=2, mode="output")

        # Blink LED while driving
        await robot.arm()
        await gpio.high(0)

        # Drive in a square
        for _ in range(4):
            await drive.drive_straight(distance=0.5, speed=0.3)
            await drive.turn(angle=90, speed=0.2)

        await gpio.low(0)
        await robot.disarm()

asyncio.run(main())
```

---

## Step 8: Adding Telemetry

Subscribe to sensor data:

```python
async def main():
    async with Robot("/dev/cu.usbserial-0001") as robot:
        # Handle IMU data
        @robot.on("telemetry.imu")
        def on_imu(data):
            print(f"Accel: {data.accel_x:.2f}, {data.accel_y:.2f}")

        # Handle encoder data
        @robot.on("telemetry.encoder0")
        def on_encoder(data):
            print(f"Velocity: {data.velocity:.2f} rad/s")

        await robot.arm()
        await asyncio.sleep(10)  # Collect data for 10s
        await robot.disarm()
```

---

## Step 9: WiFi Connection (Optional)

For wireless operation:

### Configure WiFi Credentials

Edit `firmware/mcu/include/config/WifiSecrets.h`:

```cpp
#define WIFI_STA_SSID        "YourNetwork"
#define WIFI_STA_PASSWORD    "YourPassword"
#define MQTT_BROKER_HOST     "10.0.0.59"  // Your computer's IP
```

### Flash WiFi-Enabled Firmware

```bash
pio run -e esp32_usb -t upload
```

### Start MQTT Broker (on your computer)

```bash
mara mqtt start
```

### Connect via TCP

```python
from mara_host.transport.tcp_transport import AsyncTcpTransport

transport = AsyncTcpTransport("10.0.0.60", port=3333)  # ESP32's IP
```

---

## Step 10: Calibration

### Motor Calibration

```bash
mara calibrate motor --port /dev/cu.usbserial-0001
```

### Encoder Calibration

```bash
mara calibrate encoder --port /dev/cu.usbserial-0001
```

### PID Tuning

```bash
mara calibrate pid --port /dev/cu.usbserial-0001
```

---

## Common Issues

### "Handshake timed out"

- Check USB cable (some are charge-only)
- Verify correct port: `ls /dev/cu.*`
- Try pressing ESP32 reset button

### "Command rejected: not_armed"

Always follow the safety sequence:
```python
await client.cmd_arm()      # IDLE → ARMED
await client.cmd_activate() # ARMED → ACTIVE
# ... do stuff ...
await client.cmd_stop()
await client.cmd_deactivate()
await client.cmd_disarm()
```

### Motors don't move

1. Check motor driver wiring
2. Verify PWM pins in `pins.json`
3. Test with `mara test motors --port ...`

### WiFi won't connect

1. Check credentials in `WifiSecrets.h`
2. Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
3. Check serial monitor for connection status

---

## Next Steps

- [Examples](../host/mara_host/examples/README.md) - More code examples
- [CLI Reference](ADDING_COMMANDS.md) - Full command documentation
- [Architecture](ARCHITECTURE.md) - System design
- [MQTT Guide](MQTT.md) - Multi-robot control

---

## Getting Help

- Issues: https://github.com/yourusername/mara/issues
- Examples: `host/mara_host/examples/`
