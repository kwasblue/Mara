# MARA Command Reference

Complete reference for all 117 commands in the MARA protocol.

**Generated**: April 2026
**Protocol Version**: 1
**Total Commands**: 117

---

## Table of Contents

0. [Using Commands](#using-commands)
   - [Interactive Shell](#interactive-shell)
   - [Shell Commands](#shell-commands)
   - [Send Raw Commands](#send-raw-commands)
   - [Python API](#python-api)

1. [Safety & State Management](#safety--state-management) (12 commands)
2. [Motion Control](#motion-control) (2 commands)
3. [Control System](#control-system) (18 commands)
4. [DC Motor](#dc-motor) (5 commands)
5. [Servo](#servo) (4 commands)
6. [Stepper Motor](#stepper-motor) (7 commands)
7. [GPIO & PWM](#gpio--pwm) (7 commands)
8. [Sensors](#sensors) (12 commands)
9. [Observer](#observer) (6 commands)
10. [Camera](#camera) (20 commands)
11. [Telemetry & Logging](#telemetry--logging) (5 commands)
12. [Loop Rates](#loop-rates) (4 commands)
13. [Benchmark](#benchmark) (7 commands)
14. [WiFi](#wifi) (4 commands)
15. [Batch Operations](#batch-operations) (1 command)

---

## Using Commands

There are three ways to send commands to the robot:

### Interactive Shell

Launch the interactive shell to send commands directly:

```bash
# Via serial (auto-detects port)
mara run shell -t serial

# Via serial with specific port
mara run shell -t serial -p /dev/ttyUSB0 -b 921600

# Via TCP/WiFi
mara run shell -t tcp -H 10.0.0.60 --tcp-port 3333

# Via Bluetooth
mara run shell -t ble --ble-name MARA-Robot
```

Once connected, you'll see the `mara>` prompt:

```
mara> arm
Robot armed
mara> activate
Mode set to ACTIVE
mara> servo 0 90
Servo 0 -> 90deg
mara> state
Mode: ACTIVE, Armed: True, Active: True, EStop: False
mara> quit
```

### Shell Commands

The shell provides convenient shortcuts for common operations:

#### Connection
| Command | Description |
|---------|-------------|
| `connect [type] [args]` | Connect to robot (serial, tcp, ble) |
| `disconnect` | Disconnect from robot |
| `ping` | Test connectivity |
| `status` | Show connection status |
| `quit` / `exit` | Exit shell |

#### Safety & State
| Command | Description |
|---------|-------------|
| `arm` | Arm the robot |
| `disarm` | Disarm the robot |
| `activate` / `active` | Set mode to ACTIVE |
| `deactivate` / `idle` | Set mode to IDLE |
| `estop` | Emergency stop |
| `state` | Get robot state |
| `safety` | Manage safety timeouts |

#### Actuators
| Command | Description |
|---------|-------------|
| `led [on\|off\|blink]` | Control status LED |
| `servo <id> <angle> [duration]` | Set servo angle |
| `servo attach <id> <pin>` | Attach servo to pin |
| `servo detach <id>` | Detach servo |
| `motor <id> <power>` | Set motor power (-1.0 to 1.0) |
| `stepper <id> move <steps>` | Move stepper |
| `stepper <id> enable/disable` | Enable/disable stepper |
| `gpio write <ch> <0\|1>` | Write GPIO |
| `gpio read <ch>` | Read GPIO |
| `pwm <ch> <duty> [freq]` | Set PWM |

#### Sensors
| Command | Description |
|---------|-------------|
| `encoder attach <id> <a> <b>` | Attach encoder |
| `encoder read <id>` | Read encoder |
| `encoder reset <id>` | Reset encoder count |
| `imu read` | Read IMU data |
| `imu calibrate [samples] [delay]` | Calibrate IMU |
| `ultrasonic attach <id> <trig> <echo>` | Attach ultrasonic |
| `ultrasonic read <id>` | Read distance |

#### Telemetry & System
| Command | Description |
|---------|-------------|
| `telem rate <hz>` | Set telemetry rate |
| `telem interval <ms>` | Set telemetry interval |
| `rates` | Get loop rates |
| `info` / `identity` | Get robot info |
| `version` | Show host version |

#### WiFi
| Command | Description |
|---------|-------------|
| `wifi status` | Get WiFi status |
| `wifi scan` | Scan networks |
| `wifi join <ssid> <password>` | Join network |
| `wifi disconnect` | Disconnect WiFi |

#### Control Graph
| Command | Description |
|---------|-------------|
| `ctrl status` | Get control graph status |
| `ctrl enable` | Enable control graph |
| `ctrl disable` | Disable control graph |
| `ctrl clear` | Clear control graph |

#### Events & Debug
| Command | Description |
|---------|-------------|
| `events [count\|all]` | View event history |
| `events on/off` | Toggle live event display |
| `clear` | Clear event log |
| `commands [search]` | List available MCU commands |

### Send Raw Commands

Use the `send` command to send any protocol command directly:

```bash
# Basic syntax
mara> send <COMMAND_NAME> [key=value ...]

# Examples
mara> send CMD_ARM
mara> send CMD_SET_VEL vx=0.5 omega=0.1
mara> send CMD_SERVO_SET_ANGLE servo_id=0 angle_deg=90 duration_ms=500
mara> send CMD_ENCODER_READ encoder_id=0
mara> send CMD_DC_SET_SPEED motor_id=0 speed=0.5
mara> send CMD_IMU_CALIBRATE samples=100 delay_ms=10
mara> send CMD_CTRL_SIGNAL_DEFINE id=100 name=ref signal_kind=REF initial=0.0

# CMD_ prefix is optional
mara> send ARM
mara> send SET_VEL vx=0.3 omega=0
```

**Type inference for values:**
- `true` / `false` → boolean
- Numbers with `.` → float
- Numbers without `.` → integer
- Everything else → string

**Send raw JSON:**
```bash
mara> raw {"cmd": "CMD_ARM"}
mara> raw {"cmd": "CMD_SET_VEL", "vx": 0.5, "omega": 0.1}
```

### Python API

Send commands programmatically:

```python
import asyncio
from mara_host import Robot

async def main():
    async with Robot("/dev/ttyUSB0") as robot:
        # High-level API
        await robot.arm()
        await robot.activate()
        await robot.motion.set_velocity(vx=0.5, omega=0.0)

        # Direct command access
        ok, err = await robot.client.send_reliable("CMD_SERVO_SET_ANGLE", {
            "servo_id": 0,
            "angle_deg": 90,
            "duration_ms": 300
        })

        # Fire-and-forget (no ACK)
        await robot.client.send_json("CMD_SET_VEL", {"vx": 0.0, "omega": 0.0})

        # Binary encoding (faster, for high-frequency commands)
        await robot.motion.set_velocity(vx=0.5, omega=0.1, binary=True)

        await robot.deactivate()
        await robot.disarm()

asyncio.run(main())
```

**MaraClient methods:**

| Method | Description |
|--------|-------------|
| `send_reliable(cmd, payload)` | Send with ACK/retry, returns (ok, error) |
| `send_json(cmd, payload)` | Send JSON, no ACK |
| `send_binary(opcode, data)` | Send binary frame |

---

## Safety & State Management

Commands for robot state transitions and safety systems.

### CMD_GET_IDENTITY

Get firmware version, board type, and feature flags.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Timeout | 2.0s |

**Response:**
```json
{
  "firmware_version": "1.0.0",
  "protocol_version": 1,
  "board": "esp32s3",
  "features": ["dc_motor", "servo", "encoder", "imu"]
}
```

---

### CMD_HEARTBEAT

Host heartbeat signal. Resets the MCU timeout watchdog.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Internal | Yes (not exposed as tool) |

---

### CMD_ARM

Transition robot to ARMED state. Required before ACTIVATE.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Timeout | 0.5s |

**State Transition:** `IDLE → ARMED`

---

### CMD_DISARM

Transition robot to IDLE state. Stops all motion.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Timeout | 0.5s |

**State Transition:** `ARMED → IDLE` or `ACTIVE → IDLE`

---

### CMD_ACTIVATE

Transition robot to ACTIVE state. Motion commands now accepted.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | Yes |
| Timeout | 0.5s |

**State Transition:** `ARMED → ACTIVE`

---

### CMD_DEACTIVATE

Transition robot to ARMED state. Stops motion commands.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Timeout | 0.5s |

**State Transition:** `ACTIVE → ARMED`

---

### CMD_ESTOP

Emergency stop. Immediately enters ESTOP state.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**State Transition:** `* → ESTOP`

---

### CMD_CLEAR_ESTOP

Clear emergency stop. Required after ESTOP before normal operation.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |
| Timeout | 0.5s |

**State Transition:** `ESTOP → IDLE`

---

### CMD_STOP

Soft stop. Zeros all velocities without state change.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

---

### CMD_GET_STATE

Query current robot state.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**Response:**
```json
{
  "mode": "ACTIVE",
  "armed": true,
  "active": true,
  "estop": false
}
```

---

### CMD_GET_SAFETY_TIMEOUTS

Get current safety timeout configuration.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**Response:**
```json
{
  "host_timeout_ms": 5000,
  "motion_timeout_ms": 1000,
  "enabled": true
}
```

---

### CMD_SET_SAFETY_TIMEOUTS

Configure safety timeouts. Set to 0 to disable.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| host_timeout_ms | int | Yes | Host heartbeat timeout (0 = disabled) |
| motion_timeout_ms | int | Yes | Motion command timeout (0 = disabled) |

---

## Motion Control

High-level motion commands for differential drive robots.

### CMD_SET_MODE

Set high-level robot operating mode.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**Payload:**

| Field | Type | Required | Values |
|-------|------|----------|--------|
| mode | enum | Yes | IDLE, ARMED, ACTIVE, CALIB |

---

### CMD_SET_VEL

Set linear and angular velocity in robot frame.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | Yes (ACTIVE state) |

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| vx | float | Yes | - | Linear velocity (m/s) |
| omega | float | Yes | - | Angular velocity (rad/s) |
| frame | enum | No | robot | Reference frame: robot, world |

**Example:**
```python
await client.send_reliable("CMD_SET_VEL", {"vx": 0.5, "omega": 0.1})
```

---

## Control System

Signal bus, control slots, and runtime control graphs.

### Signal Bus Commands

#### CMD_CTRL_SIGNAL_DEFINE

Define a signal in the signal bus. Only allowed in IDLE state.

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| id | int | Yes | - | Signal ID (unique) |
| name | string | Yes | - | Human-readable name |
| signal_kind | enum | Yes | - | REF, MEAS, OUT, EST |
| initial | float | No | 0.0 | Initial value |

---

#### CMD_CTRL_SIGNAL_SET

Set a signal value on the bus.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| id | int | Yes |
| value | float | Yes |

---

#### CMD_CTRL_SIGNAL_GET

Get current signal value.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| id | int | Yes |

---

#### CMD_CTRL_SIGNALS_LIST

List all defined signals.

---

#### CMD_CTRL_SIGNAL_DELETE

Delete a signal from the bus.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| id | int | Yes |

---

#### CMD_CTRL_SIGNALS_CLEAR

Clear all signals from the bus.

---

### Control Slot Commands

#### CMD_CTRL_SLOT_CONFIG

Configure a control slot with PID or state-space controller.

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| slot | int | Yes | - | Slot index (0-7) |
| controller_type | enum | Yes | - | PID, STATE_SPACE |
| rate_hz | int | Yes | - | Update rate (1-1000 Hz) |
| ref_id | int | Yes | - | Reference signal ID |
| meas_id | int | Yes | - | Measurement signal ID |
| out_id | int | Yes | - | Output signal ID |
| num_states | int | No | 1 | For state-space (1-6) |
| num_inputs | int | No | 1 | For state-space (1-2) |
| require_armed | bool | No | true | Require ARMED state |
| require_active | bool | No | true | Require ACTIVE state |

---

#### CMD_CTRL_SLOT_ENABLE

Enable or disable a control slot.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |
| enable | bool | Yes |

---

#### CMD_CTRL_SLOT_SET_PARAM

Set a scalar controller parameter.

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slot | int | Yes | Slot index |
| key | string | Yes | Parameter name (kp, ki, kd, k00, etc.) |
| value | float | Yes | Parameter value |

---

#### CMD_CTRL_SLOT_SET_PARAM_ARRAY

Set an array/matrix parameter (gain matrices K, Kr, Ki).

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |
| key | string | Yes |
| values | float[] | Yes |

---

#### CMD_CTRL_SLOT_GET_PARAM

Get a controller parameter value.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |
| key | string | Yes |

---

#### CMD_CTRL_SLOT_RESET

Reset controller internal state (integrators, etc.).

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |

---

#### CMD_CTRL_SLOT_STATUS

Get control slot status.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |

---

### Control Graph Commands

#### CMD_CTRL_GRAPH_UPLOAD

Upload a runtime control graph configuration.

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| graph | object | Yes | Graph with schema_version and slots array |

**Example:**
```json
{
  "graph": {
    "schema_version": 1,
    "slots": [
      {
        "id": "velocity_pid",
        "enabled": true,
        "rate_hz": 50,
        "source": {"type": "signal", "params": {"id": 100}},
        "transforms": [{"type": "pid", "params": {"kp": 1.0, "ki": 0.1, "kd": 0.01}}],
        "sink": {"type": "dc_motor", "params": {"motor_id": 0}}
      }
    ]
  }
}
```

---

#### CMD_CTRL_GRAPH_CLEAR

Clear the stored control graph.

---

#### CMD_CTRL_GRAPH_ENABLE

Enable or disable all control graph slots.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| enable | bool | Yes |

---

#### CMD_CTRL_GRAPH_STATUS

Get status of the stored control graph.

---

### Diagnostics Commands

#### CMD_MCU_DIAGNOSTICS_QUERY

Query persisted MCU diagnostics (boot count, errors, etc.).

---

#### CMD_MCU_DIAGNOSTICS_RESET

Reset diagnostics counters (preserves boot identity).

---

## DC Motor

Commands for DC motor control with optional closed-loop velocity PID.

### CMD_DC_SET_SPEED

Set DC motor speed (open-loop PWM).

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | Yes |
| Tool Name | motor_set |

**Payload:**

| Field | Type | Required | Range | Description |
|-------|------|----------|-------|-------------|
| motor_id | int | Yes | 0-3 | Motor index |
| speed | float | Yes | -1.0 to 1.0 | Speed (-1 = full reverse, 1 = full forward) |

---

### CMD_DC_STOP

Stop DC motor.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | Yes |
| Tool Name | motor_stop |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| motor_id | int | Yes |

---

### CMD_DC_VEL_PID_ENABLE

Enable or disable closed-loop velocity PID control.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| motor_id | int | Yes |
| enable | bool | Yes |

---

### CMD_DC_SET_VEL_TARGET

Set velocity target for PID control.

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| motor_id | int | Yes | Motor index |
| omega | float | Yes | Target velocity (rad/s) |

---

### CMD_DC_SET_VEL_GAINS

Configure velocity PID gains.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| motor_id | int | Yes |
| kp | float | Yes |
| ki | float | Yes |
| kd | float | Yes |

---

## Servo

Commands for RC servo motor control.

### CMD_SERVO_ATTACH

Attach servo to a GPIO pin.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | No |

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| servo_id | int | Yes | - | Servo index (0-7) |
| channel | int | Yes | - | GPIO pin number |
| min_us | int | No | 500 | Minimum pulse width (μs) |
| max_us | int | No | 2500 | Maximum pulse width (μs) |

---

### CMD_SERVO_DETACH

Detach servo from GPIO pin.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| servo_id | int | Yes |

---

### CMD_SERVO_SET_ANGLE

Move servo to specified angle.

| Property | Value |
|----------|-------|
| Direction | host → mcu |
| Requires ARM | Yes |
| Tool Name | servo_set |

**Payload:**

| Field | Type | Required | Default | Range |
|-------|------|----------|---------|-------|
| servo_id | int | Yes | - | 0-7 |
| angle_deg | float | Yes | - | 0-180 |
| duration_ms | int | No | 300 | Movement time |

---

### CMD_SERVO_SET_PULSE

Set servo pulse width directly.

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| servo_id | int | Yes | Servo index |
| pulse_us | int | Yes | Pulse width in microseconds |

---

## Stepper Motor

Commands for stepper motor control.

### CMD_STEPPER_ENABLE

Enable or disable stepper motor (energize/de-energize coils).

**Payload:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| stepper_id | int | Yes | - |
| enable | bool | No | true |

---

### CMD_STEPPER_MOVE_REL

Move stepper by relative number of steps.

| Property | Value |
|----------|-------|
| Tool Name | stepper_move |

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| stepper_id | int | Yes | - | Stepper index |
| steps | int | Yes | - | Steps (negative = reverse) |
| speed_rps | float | No | 1.0 | Speed in revolutions/second |

---

### CMD_STEPPER_MOVE_DEG

Move stepper by degrees.

**Payload:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| stepper_id | int | Yes | - |
| degrees | float | Yes | - |
| speed_rps | float | No | 1.0 |

---

### CMD_STEPPER_MOVE_REV

Move stepper by revolutions.

**Payload:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| stepper_id | int | Yes | - |
| revolutions | float | Yes | - |
| speed_rps | float | No | 1.0 |

---

### CMD_STEPPER_STOP

Stop stepper motor movement.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| stepper_id | int | Yes |

---

### CMD_STEPPER_GET_POSITION

Get current stepper position in steps.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| stepper_id | int | Yes |

---

### CMD_STEPPER_RESET_POSITION

Reset stepper position counter to zero.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| stepper_id | int | Yes |

---

## GPIO & PWM

General-purpose I/O and PWM control.

### CMD_LED_ON

Turn status LED on.

| Property | Value |
|----------|-------|
| Requires ARM | No |

---

### CMD_LED_OFF

Turn status LED off.

| Property | Value |
|----------|-------|
| Requires ARM | No |

---

### CMD_GPIO_REGISTER_CHANNEL

Register a GPIO channel mapping logical ID to physical pin.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required | Default | Values |
|-------|------|----------|---------|--------|
| channel | int | Yes | - | Logical channel ID |
| pin | int | Yes | - | Physical GPIO pin |
| mode | enum | No | output | output, input, input_pullup |

---

### CMD_GPIO_WRITE

Set GPIO pin high or low.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| channel | int | Yes |
| value | int | Yes (0 or 1) |

---

### CMD_GPIO_READ

Read GPIO pin state.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| channel | int | Yes |

---

### CMD_GPIO_TOGGLE

Toggle GPIO pin state.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| channel | int | Yes |

---

### CMD_PWM_SET

Set PWM duty cycle.

**Payload:**

| Field | Type | Required | Range | Description |
|-------|------|----------|-------|-------------|
| channel | int | Yes | - | PWM channel |
| duty | float | Yes | 0.0-1.0 | Duty cycle |
| freq_hz | float | No | - | Frequency (Hz) |

---

## Sensors

Sensor attachment, reading, and calibration.

### IMU Commands

#### CMD_IMU_READ

Read IMU sensor data (accelerometer + gyroscope).

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Response:**
```json
{
  "ax": 0.01, "ay": -0.02, "az": 9.81,
  "gx": 0.001, "gy": -0.002, "gz": 0.0
}
```

---

#### CMD_IMU_CALIBRATE

Auto-calibrate IMU bias offsets.

**Payload:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| samples | int | No | 100 |
| delay_ms | int | No | 10 |

---

#### CMD_IMU_SET_BIAS

Manually set IMU bias offsets.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| accel_bias | float[3] | Yes |
| gyro_bias | float[3] | Yes |

---

#### CMD_IMU_ZERO

Reset IMU orientation (zero yaw/heading).

---

#### CMD_I2C_SCAN

Scan I2C bus and report responding addresses.

| Property | Value |
|----------|-------|
| Tool Name | i2c_scan |

---

### Ultrasonic Commands

#### CMD_ULTRASONIC_ATTACH

Attach ultrasonic distance sensor.

**Payload:**

| Field | Type | Required | Default | Range |
|-------|------|----------|---------|-------|
| sensor_id | int | Yes | - | 0-3 |
| trig_pin | int | Yes | - | GPIO pin |
| echo_pin | int | Yes | - | GPIO pin |
| max_distance_cm | float | No | 400.0 | Max range |

---

#### CMD_ULTRASONIC_READ

Read distance from ultrasonic sensor.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| sensor_id | int | Yes |

**Response:**
```json
{"distance_cm": 42.5}
```

---

#### CMD_ULTRASONIC_DETACH

Detach ultrasonic sensor.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| sensor_id | int | Yes |

---

### Encoder Commands

#### CMD_ENCODER_ATTACH

Attach quadrature encoder.

**Payload:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| encoder_id | int | Yes | - | Encoder index |
| pin_a | int | Yes | - | Channel A GPIO |
| pin_b | int | Yes | - | Channel B GPIO |
| ppr | int | No | 11 | Pulses per revolution |
| gear_ratio | float | No | 1.0 | Gear reduction ratio |

---

#### CMD_ENCODER_READ

Read encoder position and velocity.

| Property | Value |
|----------|-------|
| Requires ARM | No |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| encoder_id | int | Yes |

**Response:**
```json
{"position": 1234, "velocity": 5.2}
```

---

#### CMD_ENCODER_RESET

Reset encoder count to zero.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| encoder_id | int | Yes |

---

#### CMD_ENCODER_DETACH

Detach encoder.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| encoder_id | int | Yes |

---

## Observer

Luenberger state observer configuration.

### CMD_OBSERVER_CONFIG

Configure a state observer slot.

**Payload:**

| Field | Type | Required | Range |
|-------|------|----------|-------|
| slot | int | Yes | 0-3 |
| num_states | int | Yes | 1-6 |
| num_inputs | int | Yes | 1-2 |
| num_outputs | int | Yes | 1-4 |
| rate_hz | int | Yes | 50-1000 |
| input_ids | int[] | Yes | Signal IDs |
| output_ids | int[] | Yes | Signal IDs |
| estimate_ids | int[] | Yes | Signal IDs |

---

### CMD_OBSERVER_ENABLE

Enable or disable observer.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |
| enable | bool | Yes |

---

### CMD_OBSERVER_RESET

Reset observer state estimate to zero.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |

---

### CMD_OBSERVER_SET_PARAM

Set individual matrix element.

**Payload:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slot | int | Yes | Observer slot |
| key | string | Yes | Element key (A01, L10, etc.) |
| value | float | Yes | Element value |

---

### CMD_OBSERVER_SET_PARAM_ARRAY

Set full matrix in row-major order.

**Payload:**

| Field | Type | Required | Values |
|-------|------|----------|--------|
| slot | int | Yes | 0-3 |
| key | enum | Yes | A, B, C, L |
| values | float[] | Yes | Matrix elements |

---

### CMD_OBSERVER_STATUS

Get observer status and current state estimates.

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| slot | int | Yes |

---

## Camera

ESP32-CAM control commands (sent to camera module, not MCU).

### CMD_CAM_GET_STATUS

Get camera device status.

**Payload:**

| Field | Type | Default |
|-------|------|---------|
| camera_id | int | 0 |

**Response:**
```json
{"ip": "10.0.0.66", "rssi": -45, "heap": 123456, "uptime": 3600}
```

---

### CMD_CAM_GET_CONFIG

Get current camera configuration.

---

### CMD_CAM_SET_RESOLUTION

Set camera resolution.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| camera_id | int | 0 |
| size | int | 0-13 (QQVGA to UXGA) |

**Resolution Values:**
- 0: QQVGA (160x120)
- 5: QVGA (320x240)
- 8: VGA (640x480)
- 10: XGA (1024x768)
- 13: UXGA (1600x1200)

---

### CMD_CAM_SET_QUALITY

Set JPEG compression quality.

**Payload:**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| quality | int | 4-63 | Lower = better quality |

---

### CMD_CAM_SET_BRIGHTNESS / CONTRAST / SATURATION / SHARPNESS

Adjust image parameters.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| brightness/contrast/saturation/sharpness | int | -2 to 2 |

---

### CMD_CAM_SET_FLIP

Set image flip/mirror.

**Payload:**

| Field | Type |
|-------|------|
| hmirror | bool |
| vflip | bool |

---

### CMD_CAM_SET_AWB

Configure auto white balance.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| enabled | bool | - |
| mode | int | 0-4 (Auto/Sunny/Cloudy/Office/Home) |

---

### CMD_CAM_SET_EXPOSURE

Configure exposure.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| auto | bool | - |
| value | int | 0-1200 |

---

### CMD_CAM_SET_GAIN

Configure gain control.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| auto | bool | - |
| value | int | 0-30 |
| ceiling | int | 0-6 |

---

### CMD_CAM_FLASH

Control flash LED.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| state | enum | on, off, toggle |

---

### CMD_CAM_APPLY_PRESET

Apply predefined configuration preset.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| preset | enum | default, streaming, high_quality, fast, night, ml_inference |

---

### CMD_CAM_START_CAPTURE

Start continuous frame capture.

**Payload:**

| Field | Type | Default | Values |
|-------|------|---------|--------|
| mode | enum | polling | polling, streaming |
| fps | float | 10.0 | Target framerate |

---

### CMD_CAM_STOP_CAPTURE

Stop continuous capture.

---

### CMD_CAM_CAPTURE_FRAME

Capture a single frame.

**Payload:**

| Field | Type | Default |
|-------|------|---------|
| publish | bool | true |

---

### CMD_CAM_START_RECORDING / STOP_RECORDING

Control frame recording to disk.

**Payload (start):**

| Field | Type | Default | Values |
|-------|------|---------|--------|
| output_dir | string | "recordings" | - |
| format | enum | - | video, frames |

---

### CMD_CAM_SET_MOTION_DETECTION

Configure motion detection.

**Payload:**

| Field | Type | Default | Range |
|-------|------|---------|-------|
| enabled | bool | - | - |
| sensitivity | int | 30 | 1-100 |

---

## Telemetry & Logging

Telemetry configuration and MCU logging.

### CMD_TELEM_SET_INTERVAL

Set telemetry publish interval.

**Payload:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| interval_ms | int | 100 | 0 = disabled |

---

### CMD_SET_LOG_LEVEL

Set MCU global logging verbosity.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| level | enum | debug, info, warn, error, off |

---

### CMD_SET_SUBSYSTEM_LOG_LEVEL

Set logging for specific subsystem.

**Payload:**

| Field | Type | Values |
|-------|------|--------|
| subsystem | string | servo, stepper, motor, gpio, system |
| level | enum | debug, info, warn, error, off |

---

### CMD_GET_LOG_LEVELS

Get current MCU log levels.

---

### CMD_CLEAR_SUBSYSTEM_LOG_LEVELS

Clear all per-subsystem log levels (revert to global).

---

## Loop Rates

Configure MCU loop rates (only in IDLE state).

### CMD_GET_RATES

Get current loop rates.

**Response:**
```json
{"ctrl_hz": 100, "safety_hz": 200, "telem_hz": 50}
```

---

### CMD_CTRL_SET_RATE

Set control loop rate.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| hz | int | 5-200 |

---

### CMD_SAFETY_SET_RATE

Set safety loop rate.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| hz | int | 20-500 |

---

### CMD_TELEM_SET_RATE

Set telemetry loop rate.

**Payload:**

| Field | Type | Range |
|-------|------|-------|
| hz | int | 1-50 |

---

## Benchmark

MCU performance benchmarking.

### CMD_BENCH_START

Start a benchmark test.

**Payload:**

| Field | Type | Default | Range |
|-------|------|---------|-------|
| test_id | int | - | 0-255 |
| iterations | int | 100 | 1-10000 |
| warmup | int | 10 | 0-1000 |
| budget_us | int | 0 | - |
| rt_safe | bool | false | - |
| stream | bool | false | - |

---

### CMD_BENCH_STOP

Cancel all running/queued benchmarks.

---

### CMD_BENCH_STATUS

Get benchmark system status.

---

### CMD_BENCH_LIST_TESTS

List all available benchmark tests.

---

### CMD_BENCH_GET_RESULTS

Get benchmark result history.

**Payload:**

| Field | Type | Default | Range |
|-------|------|---------|-------|
| max | int | 4 | 1-8 |

---

### CMD_BENCH_RUN_BOOT_TESTS

Manually trigger boot-time benchmarks.

---

### CMD_PERF_RESET

Reset MCU performance counters.

---

## WiFi

WiFi connection management.

### CMD_WIFI_SCAN

Scan for available WiFi networks.

| Property | Value |
|----------|-------|
| Timeout | 10.0s |

**Response:**
```json
{
  "networks": [
    {"ssid": "MyNetwork", "rssi": -45, "encrypted": true},
    {"ssid": "Guest", "rssi": -60, "encrypted": false}
  ]
}
```

---

### CMD_WIFI_JOIN

Connect to WiFi network.

| Property | Value |
|----------|-------|
| Timeout | 15.0s |

**Payload:**

| Field | Type | Required |
|-------|------|----------|
| ssid | string | Yes |
| password | string | No |

---

### CMD_WIFI_DISCONNECT

Disconnect from current WiFi.

| Property | Value |
|----------|-------|
| Timeout | 2.0s |

---

### CMD_WIFI_STATUS

Get WiFi connection status.

**Response:**
```json
{"connected": true, "ssid": "MyNetwork", "rssi": -45, "ip": "10.0.0.60"}
```

---

## Batch Operations

Execute multiple commands atomically.

### CMD_BATCH_APPLY

Apply a batch of commands.

**Payload:**

| Field | Type | Description |
|-------|------|-------------|
| actions | array | Array of {cmd, args} objects |

**Batchable Commands:**
- GPIO_WRITE
- SERVO_SET_ANGLE
- PWM_SET
- DC_SET_SPEED
- DC_STOP
- STEPPER_MOVE_REL
- STEPPER_STOP

**Example:**
```json
{
  "actions": [
    {"cmd": "GPIO_WRITE", "args": {"channel": 0, "value": 1}},
    {"cmd": "SERVO_SET_ANGLE", "args": {"servo_id": 0, "angle_deg": 90}},
    {"cmd": "DC_SET_SPEED", "args": {"motor_id": 0, "speed": 0.5}}
  ]
}
```

---

## State Machine Reference

```
                    ┌─────────────┐
                    │    ESTOP    │
                    └──────┬──────┘
                           │ CMD_CLEAR_ESTOP
                           ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    IDLE     │◄───│   ARMED     │◄───│   ACTIVE    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │ CMD_ARM          │ CMD_ACTIVATE     │
       └─────────────────►└─────────────────►│
       │                  │                  │
       │ CMD_DISARM       │ CMD_DEACTIVATE   │
       │◄─────────────────│◄─────────────────┘
```

**Transitions:**
- `IDLE → ARMED`: CMD_ARM
- `ARMED → ACTIVE`: CMD_ACTIVATE
- `ACTIVE → ARMED`: CMD_DEACTIVATE
- `ARMED → IDLE`: CMD_DISARM
- `* → ESTOP`: CMD_ESTOP
- `ESTOP → IDLE`: CMD_CLEAR_ESTOP

---

## Quick Reference by Category

| Category | Commands |
|----------|----------|
| **State** | ARM, DISARM, ACTIVATE, DEACTIVATE, ESTOP, CLEAR_ESTOP, STOP, GET_STATE |
| **Motion** | SET_VEL, SET_MODE |
| **DC Motor** | DC_SET_SPEED, DC_STOP, DC_VEL_PID_ENABLE, DC_SET_VEL_TARGET, DC_SET_VEL_GAINS |
| **Servo** | SERVO_ATTACH, SERVO_DETACH, SERVO_SET_ANGLE, SERVO_SET_PULSE |
| **Stepper** | STEPPER_ENABLE, STEPPER_MOVE_REL/DEG/REV, STEPPER_STOP, STEPPER_GET/RESET_POSITION |
| **GPIO** | GPIO_REGISTER_CHANNEL, GPIO_READ, GPIO_WRITE, GPIO_TOGGLE, LED_ON/OFF |
| **PWM** | PWM_SET |
| **IMU** | IMU_READ, IMU_CALIBRATE, IMU_SET_BIAS, IMU_ZERO, I2C_SCAN |
| **Encoder** | ENCODER_ATTACH, ENCODER_READ, ENCODER_RESET, ENCODER_DETACH |
| **Ultrasonic** | ULTRASONIC_ATTACH, ULTRASONIC_READ, ULTRASONIC_DETACH |
| **Control** | CTRL_SIGNAL_*, CTRL_SLOT_*, CTRL_GRAPH_* |
| **Observer** | OBSERVER_CONFIG, OBSERVER_ENABLE, OBSERVER_RESET, OBSERVER_SET_PARAM* |
| **Telemetry** | TELEM_SET_INTERVAL, TELEM_SET_RATE |
| **Logging** | SET_LOG_LEVEL, SET_SUBSYSTEM_LOG_LEVEL, GET_LOG_LEVELS |
| **WiFi** | WIFI_SCAN, WIFI_JOIN, WIFI_DISCONNECT, WIFI_STATUS |
| **System** | GET_IDENTITY, HEARTBEAT, GET_RATES, *_SET_RATE |
| **Benchmark** | BENCH_START, BENCH_STOP, BENCH_STATUS, BENCH_LIST_TESTS, BENCH_GET_RESULTS |
