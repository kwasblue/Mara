# Robot Abstraction Layer

<div align="center">

**Semantic robot control for LLM integration**

*Move joints by name, not hardware IDs*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Overview

The Robot Abstraction Layer provides semantic control over robots, mapping joint names (like "shoulder") to hardware IDs (like `servo_id=0`). This enables LLMs to reason about robot movements without knowing the underlying hardware.

```
┌─────────────────────────────────────────────────────┐
│              Robot Layer                            │
│  "Move shoulder to 45°"  →  "shoulder" → servo 0   │
│  "Home all joints"       →  coordinates all moves   │
│  "Describe robot"        →  LLM-readable structure  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│           Services Layer (existing)                 │
│  ServoService, MotorService, StepperService        │
│  StateService, TelemetryService                    │
└─────────────────────────────────────────────────────┘
```

**Key features:**
- **Generic design** — Works with any robot via YAML configuration
- **Joint-based control** — Move by semantic names, not hardware IDs
- **Coordinated movement** — Multiple joints move simultaneously
- **Pose tracking** — Track positions with freshness indicators
- **LLM-friendly** — Descriptions tell the LLM what each joint does
- **Additive** — Doesn't modify existing services; you can still use component tools directly

---

## Quick Start

### 1. Create a Robot Configuration

```yaml
# robots/my_robot.yaml
name: "my_robot"
description: "My custom robot"
type: "manipulator"

joints:
  shoulder:
    actuator: servo
    actuator_id: 0
    pin: 18
    min_angle: 0
    max_angle: 180
    home: 90
    zero_position: "pointing down"
    max_position: "pointing up"

  elbow:
    actuator: servo
    actuator_id: 1
    pin: 19
    min_angle: 30
    max_angle: 150
    home: 90
    parent: shoulder  # Kinematic relationship

chains:
  arm: [shoulder, elbow]
```

### 2. Load and Control

```python
from mara_host.robot_layer import load_robot_model, RobotService

# Load robot model
model = load_robot_model("robots/my_robot.yaml")

# Create service with hardware services
robot = RobotService(model, servo_service=servo_service)

# Move by joint name
await robot.move_joint("shoulder", 45)

# Move multiple joints simultaneously
await robot.move_joints([
    {"joint": "shoulder", "angle": 60},
    {"joint": "elbow", "angle": 45},
])

# Home all joints
await robot.home()

# Get LLM-readable description
print(robot.describe())
```

---

## YAML Configuration Format

### Required Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | string | Robot identifier |
| `type` | string | Robot type (manipulator, mobile, etc.) |
| `joints` | dict | Joint definitions |

### Joint Fields

| Field | Type | Required | Default | Description |
|:------|:-----|:---------|:--------|:------------|
| `actuator` | string | ✓ | — | `servo`, `dc_motor`, or `stepper` |
| `actuator_id` | int | ✓ | — | Hardware ID (servo_id, motor_id, etc.) |
| `type` | string | | `revolute` | `revolute`, `prismatic`, `continuous` |
| `pin` | int | | — | GPIO pin for attachment |
| `min_angle` | float | | `0` | Minimum position in degrees |
| `max_angle` | float | | `180` | Maximum position in degrees |
| `home` | float | | `90` | Home position in degrees |
| `max_velocity` | float | | — | Speed limit in degrees/second |
| `zero_position` | string | | — | Description at min_angle (for LLM) |
| `max_position` | string | | — | Description at max_angle (for LLM) |
| `parent` | string | | — | Parent joint name for kinematic chain |

### Optional Sections

```yaml
# Kinematic chains: ordered joint sequences
chains:
  arm: [shoulder, elbow, wrist]

# Groups: joints controlled together
groups:
  upper_arm: [shoulder, elbow]
  end_effector: [gripper]
```

---

## MCP Tools

The robot layer exposes 5 MCP tools for LLM control:

| Tool | Description |
|:-----|:------------|
| `mara_robot_describe` | Get robot structure, joint limits, and relationships |
| `mara_robot_state` | Get safety state, positions, and sensor readings |
| `mara_robot_pose` | Get current joint positions with freshness |
| `mara_robot_move` | Move one or more joints by name |
| `mara_robot_home` | Move joints to home positions |

### robot_describe

Returns LLM-readable robot description:

```
# Robot: arm_3dof
Type: manipulator
Description: 3-DOF robotic arm with gripper

## Joints

### shoulder (base)
- Range: 0° to 180°
- Home: 90°
- At 0°: pointing straight down
- At 180°: pointing straight up

### elbow (attached to shoulder)
- Range: 30° to 150°
- Home: 90°
- At 30°: fully extended (straight arm)
- At 150°: fully folded back
```

### robot_move

Move joints by name:

```json
{
  "moves": "[{\"joint\": \"shoulder\", \"angle\": 45}, {\"joint\": \"elbow\", \"angle\": 90}]",
  "duration_ms": 300
}
```

### robot_pose

Returns current positions with freshness:

```
shoulder: 45.0° (67% of range) ● fresh
elbow: 90.0° (50% of range) ○ recent
gripper: 60.0° (0% of range) ⚠ stale

● fresh (<1s)  ○ recent (<5s)  ⚠ stale (>5s)  ? unknown
```

---

## Pose Tracking

The `PoseTracker` maintains joint state with freshness indicators:

```python
from mara_host.robot_layer import PoseTracker

tracker = PoseTracker(model)

# Record commanded position
tracker.record_command("shoulder", 45)

# Get current pose
pose = tracker.get_current()  # {"shoulder": 45, "elbow": 90, ...}

# Check freshness
freshness = tracker.get_freshness("shoulder")  # "fresh", "recent", "stale", "unknown"
```

**Freshness levels:**
- `fresh` — Updated < 1 second ago
- `recent` — Updated < 5 seconds ago
- `stale` — Updated > 5 seconds ago
- `unknown` — Never updated (using home position)

---

## Safety Architecture

The robot layer integrates with the existing multi-layer safety system:

```
┌─────────────────────────────────────────────────────┐
│  Robot Layer: Semantic validation                   │
│  - Joint exists?                                    │
│  - Angle within limits?                             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Host Services: Soft limits                         │
│  - Clamp angles to safe range                       │
│  - Coordinate movements                             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Protocol: Reliable delivery                        │
│  - CRC validation                                   │
│  - ACK/retry                                        │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  Firmware: Hard limits                              │
│  - State machine (IDLE/ARMED/ESTOP)                │
│  - Hardware limits                                  │
│  - Watchdog timer                                   │
└─────────────────────────────────────────────────────┘
```

**You can still access any layer directly:**
- Robot tools: `mara_robot_move` (semantic names)
- Component tools: `mara_servo_set` (hardware IDs)
- Direct client: `robot.client.servo_set_angle()` (raw protocol)

---

## API Reference

### RobotModel

```python
model = load_robot_model("path/to/config.yaml")

# Query joints
joint = model.get_joint("shoulder")  # Returns Joint
exists = model.has_joint("shoulder")  # Returns bool
roots = model.get_root_joints()       # Joints without parents
children = model.get_children("shoulder")  # Child joints

# Filter by actuator type
servos = model.get_joints_by_actuator(ActuatorType.SERVO)
```

### Joint

```python
joint = model.get_joint("shoulder")

# Validate angle
valid, error = joint.validate_angle(200)  # (False, "above max (180)")

# Clamp to limits
safe_angle = joint.clamp_angle(200)  # Returns 180
```

### RobotService

```python
robot = RobotService(
    model,
    servo_service=servo_service,
    motor_service=motor_service,
    stepper_service=stepper_service,
)

# Single joint
result = await robot.move_joint("shoulder", 45)

# Multiple joints (simultaneous)
result = await robot.move_joints([
    {"joint": "shoulder", "angle": 45},
    {"joint": "elbow", "angle": 90},
])

# Home positions
result = await robot.home()                    # All joints
result = await robot.home(["shoulder"])        # Specific joints

# State
pose = robot.get_pose()    # {"shoulder": 45, ...}
desc = robot.describe()    # LLM-readable string
```

### Trajectory Execution

For smooth multi-waypoint motion (from diffusion policies, motion planning, etc.):

```python
from mara_host.robot_layer import Trajectory, Waypoint

# Execute trajectory from list of waypoints
waypoints = [
    {"shoulder": 45, "elbow": 90},
    {"shoulder": 60, "elbow": 75},
    {"shoulder": 90, "elbow": 60},
]
result = await robot.execute_trajectory(waypoints, frequency_hz=20)

# Or from Trajectory object (more control)
traj = Trajectory(waypoints=[
    Waypoint(joints={"shoulder": 45}, duration_ms=100),
    Waypoint(joints={"shoulder": 90}, duration_ms=100),
])
result = await robot.execute_trajectory(traj)

# Background execution with cancellation
execution = robot.start_trajectory(waypoints, frequency_hz=20)

# Monitor progress
print(f"Progress: {execution.progress:.0%}")

# Cancel if needed
execution.cancel()

# Wait for completion
await execution.wait()
```

| Method | Use Case |
|:-------|:---------|
| `execute_trajectory()` | Blocking execution, returns when complete |
| `start_trajectory()` | Non-blocking, returns handle for monitoring/cancellation |

### RobotStateContext

```python
from mara_host.robot_layer import RobotStateContext

ctx = RobotStateContext(model, pose_tracker)

# For LLM system prompt
system_context = ctx.get_system_context()

# State summary
summary = ctx.get_state_summary()

# Formatted pose
pose_text = ctx.format_pose()
```

---

## Example: LLM Control Flow

```
┌─────────────────────────────────────────────────────┐
│ LLM: "I want to pick up an object"                  │
│                                                     │
│ 1. Call robot_describe to understand structure      │
│    → Learns: shoulder (down↔up), elbow, gripper    │
│                                                     │
│ 2. Call robot_pose to see current state             │
│    → Sees: shoulder=90°, elbow=90°, gripper=open   │
│                                                     │
│ 3. Reason about required movement                   │
│    → "Need to lower arm and close gripper"          │
│                                                     │
│ 4. Call robot_move to execute                       │
│    → [shoulder→45°, elbow→120°]                    │
│                                                     │
│ 5. Call robot_move for gripper                      │
│    → [gripper→120°]                                │
└─────────────────────────────────────────────────────┘
```

**No pre-defined poses needed** — the LLM generates movements from joint descriptions.

---

## Files

| File | Purpose |
|:-----|:--------|
| `robot_layer/__init__.py` | Package exports |
| `robot_layer/model.py` | RobotModel, Joint, enums |
| `robot_layer/loader.py` | YAML loading and validation |
| `robot_layer/pose.py` | PoseTracker for state tracking |
| `robot_layer/service.py` | RobotService for control |
| `robot_layer/context.py` | LLM context generation |
| `robots/*.yaml` | Robot configurations |

---

<div align="center">

*Semantic control for any robot*

</div>
