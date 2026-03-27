# Robot Host Examples

Comprehensive examples demonstrating the mara_host platform for controlling ESP32-based robots.

## Prerequisites

1. **Hardware**: ESP32 with mara_host firmware flashed
2. **Connection**: USB cable (serial) or WiFi (TCP)
3. **Python packages**: Install with `pip install pyserial`

## Quick Start

The recommended way to use mara_host - direct service access:

```python
from mara_host import Robot

async def main():
    async with Robot("/dev/ttyUSB0") as robot:
        await robot.arm()

        # Direct service access via Robot properties
        await robot.gpio.write(channel=0, value=1)
        await robot.gpio.set_pwm(channel=0, duty=0.5, freq_hz=1000)
        await robot.motion.set_velocity(vx=0.2, omega=0.0)

        await robot.motion.stop()

asyncio.run(main())
```

```bash
# Run the getting started example
python examples/00_getting_started.py
```

## Examples Overview

### Core Examples

| Example | Description | Focus |
|---------|-------------|-------|
| 00 | Getting Started | Basic connection and service usage |
| 10 | Custom Robot Class | Building your own robot abstraction |
| 11 | Sensors and Telemetry | Encoder, IMU, Ultrasonic |
| 12 | Velocity Control | High-rate streaming for differential drive |
| 13 | IMU to Servo Prototype | Map accel-based pitch/roll to servo 0 safely |

### Legacy Examples (Low-Level API)

| Example | Description | Requires Hardware |
|---------|-------------|-------------------|
| 01 | Serial connection and handshake | ESP32 via USB |
| 02 | TCP/WiFi connection | ESP32 with WiFi |
| 03 | Command basics (ARM, ACKs) | ESP32 |
| 04 | Telemetry streaming | ESP32 with sensors |
| 05 | GPIO control (LEDs, buttons) | ESP32 + LED |
| 06 | Motor control and motion | ESP32 + motors |
| 07 | Encoder feedback | ESP32 + encoders |
| 08 | Session recording | ESP32 |
| 09 | Full robot control | Complete robot |

## Core Examples

### 00: Getting Started
Basic connection and service usage:

```bash
python examples/00_getting_started.py
```

### 10: Custom Robot Class
Build YOUR robot as a Python class using the API layer:

```python
from mara_host import Robot
from mara_host.api import Stepper

class PillDispenser:
    def __init__(self, robot: Robot):
        self._robot = robot
        self._stepper = Stepper(robot, stepper_id=0)

    async def dispense(self, count: int):
        for _ in range(count):
            await self._stepper.move(steps=40)
            await asyncio.sleep(0.5)
```

### 11: Sensors and Telemetry
Reading encoders, IMU, and ultrasonic sensors:

```python
from mara_host import Robot, Encoder

async with Robot("/dev/ttyUSB0") as robot:
    encoder = Encoder(robot, pin_a=32, pin_b=33)
    await encoder.attach()

    # Callback-based updates
    encoder.on_update(lambda r: print(f"Count: {r.count}"))
```

### 12: Velocity Control
High-rate velocity streaming using MotionService:

```python
from mara_host import Robot

async with Robot("/dev/ttyUSB0") as robot:
    # Direct access via Robot property
    while running:
        await robot.motion.set_velocity(vx=0.5, omega=0.1)
        await asyncio.sleep(0.02)  # 50Hz
```

### 13: IMU to Servo Prototype
Tie one accel-derived IMU axis to servo 0 using the explicit IMU snapshot path and the existing servo service:

```bash
python examples/13_imu_to_servo.py --port /dev/ttyUSB0 --pin 18 --axis pitch
```

Useful tuning flags:
- `--axis pitch|roll`
- `--tilt-limit-deg 25`
- `--servo-span-deg 20`
- `--deadband-deg 2`
- `--smoothing-alpha 0.25`
- `--interval-s 0.20`
- `--dry-run`

Safety behavior:
- centers the servo first
- defaults to a narrow clamp (`60..120` deg)
- detaches the servo and disarms the robot on Ctrl+C / exit

### MCU Control-Graph JSON Presets
Ready-to-run MCU-native graph presets live in:

- `examples/control_graphs/imu_pitch_servo_safe.json`
- `examples/control_graphs/imu_pitch_servo_snappy.json`

Apply one with:

```bash
mara control graph-apply examples/control_graphs/imu_pitch_servo_safe.json
mara control graph-status
```

Notes:
- upload/apply must happen while the robot is `IDLE`
- these files only configure the graph; you still need servo 0 attached on the right pin before expecting motion
- if direction is backwards, insert a `scale` transform with factor `-1.0` before the offset stage

## Examples in Detail

### 01: Serial Connection
Basic USB/serial connection to ESP32:
- Automatic port detection
- Version handshake
- Connection monitoring

```bash
python 01_serial_connection.py
python 01_serial_connection.py /dev/ttyUSB0
python 01_serial_connection.py COM3  # Windows
```

### 02: TCP Connection
WiFi/network connection:
- TCP transport with auto-reconnect
- Works over local network

```bash
python 02_tcp_connection.py 192.168.1.100
python 02_tcp_connection.py 192.168.1.100 8080  # custom port
```

### 03: Command Basics
Sending commands and handling responses:
- Fire-and-forget commands
- Reliable commands with ACK
- Robot state machine (ARM/ACTIVATE/DISARM)
- Error handling

```bash
python 03_command_basics.py /dev/ttyUSB0
python 03_command_basics.py tcp:192.168.1.100
```

### 04: Telemetry Stream
Receiving sensor data:
- IMU (accelerometer, gyroscope)
- Encoders
- Motor data
- Ultrasonic sensors

```bash
python 04_telemetry_stream.py /dev/ttyUSB0
```

### 05: GPIO Control
Controlling GPIO pins:
- Write (LEDs, relays)
- Read (buttons, switches)
- Toggle
- Pattern generation (SOS)

```bash
python 05_gpio_control.py /dev/ttyUSB0
```

### 06: Motor Control
**WARNING: Robot will move!**

Motor and motion control:
- ARM/ACTIVATE sequence
- Velocity commands
- Velocity ramping
- Emergency stop (ESTOP)
- Arc motion

```bash
python 06_motor_control.py /dev/ttyUSB0
```

### 07: Encoder Feedback
Reading quadrature encoders:
- Attach encoders to pins
- Read tick counts
- Compute velocity
- Real-time display

```bash
python 07_encoder_feedback.py /dev/ttyUSB0
```

### 08: Session Recording
Recording and replaying sessions:
- Record all events to JSONL
- Analyze recorded sessions
- Replay at different speeds

```bash
python 08_session_recording.py /dev/ttyUSB0
# Creates recordings in ./recordings/
```

### 09: Full Robot Control
**WARNING: Robot will move!**

Complete control application:
- Connection management
- State machine
- Real-time telemetry
- Safety monitoring
- Demo trajectories (square, figure-8)
- Session recording

```bash
python 09_full_robot_control.py /dev/ttyUSB0
```

## Connection Argument Format

All examples accept a connection argument:

```bash
# Serial (USB)
python example.py /dev/ttyUSB0        # Linux
python example.py /dev/tty.usbserial-XXXX  # macOS
python example.py COM3                 # Windows

# TCP (WiFi)
python example.py tcp:192.168.1.100   # Default port 8080
python example.py tcp:192.168.1.100:9000  # Custom port
```

## Output Files

Some examples create output files:

- `recordings/` - Session recordings (example 08)
- `control_logs/` - Control session logs (example 09)
- `*.png` - Generated plots

## Troubleshooting

### Serial Connection Issues

1. **Port not found**:
   - Check USB cable is connected
   - Run `ls /dev/tty*` (Linux/macOS) or check Device Manager (Windows)

2. **Permission denied** (Linux):
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in
   ```

3. **Port busy**:
   - Close other programs using the port
   - Unplug and replug USB cable

### TCP Connection Issues

1. **Connection refused**:
   - Verify ESP32 IP address
   - Check ESP32 serial output for IP
   - Ensure both on same network

2. **Timeout**:
   - Check firewall settings
   - Try pinging the ESP32 IP

### Handshake Failures

1. **Protocol version mismatch**:
   - Update firmware or host to match versions

2. **Timeout**:
   - Reset ESP32
   - Check baud rate (115200)

## Safety Notes

- Examples 06 and 09 move motors - **ensure safe environment**
- Always have an emergency stop ready (unplug power)
- Start with low velocities when testing
- The ESTOP command immediately stops all motion

## See Also

- `mara_host/research/examples/` - Research and analysis examples
- `mara_host/runners/` - Additional utility scripts
