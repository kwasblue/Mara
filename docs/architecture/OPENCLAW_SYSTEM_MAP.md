# OpenClaw System Map for MARA

This document is a repo-native system map written from the `openclaw/workbench` branch.

It is meant to answer a practical question:

> If an agent or operator needs to understand, debug, or safely modify MARA, where are the real control points?

It complements the existing architecture docs by focusing on:
- actual entrypoints
- control/data flow
- where abstractions converge
- what is authoritative vs generated
- what currently looks important or fragile

---

## 1. High-level shape

MARA is a robotics monorepo with three major runtime surfaces:

1. **MCU firmware** (`firmware/mcu/`)
   - real-time control on ESP32
   - safety, setup, command handling, telemetry, transport
2. **Host software** (`host/mara_host/`)
   - Python client, services, CLI, GUI, workflows, MCP/HTTP runtime
3. **Camera firmware** (`firmware/cam/`)
   - ESP32-CAM subsystem with separate networked vision path

For most non-vision work, the effective stack is:

```text
Agent / Operator
  -> CLI or MCP/HTTP
  -> host services
  -> MaraClient
  -> transport (serial/TCP/CAN/MQTT)
  -> ESP32 firmware
```

---

## 2. The most important architectural fact

The system is built around a **shared host service layer**.

That means:
- the **CLI** is mostly a user-facing shell over services
- the **MCP/HTTP runtime** is mostly an agent-facing shell over services
- the **transport/client layer** is the single path to the MCU

In practice, if you want to change system behavior without breaking everything:
- change business rules in `services/`
- change wire behavior in `command/` or `transport/`
- change LLM exposure in `mcp/tool_schema.py`
- change hardware behavior in firmware modules/setup/handlers

This convergence is one of the repo's strongest design choices.

---

## 3. Firmware mental model

### 3.1 MCU entrypoint

The main firmware entrypoint is:
- `firmware/mcu/src/main.cpp`

Its boot flow is staged:

1. initialize HAL and service storage
2. initialize transports, router, commands, control, host
3. build `ServiceContext`
4. run setup modules from manifest
5. start FreeRTOS control task
6. run rate-limited loops for:
   - safety
   - control
   - telemetry
   - sensors
   - host/router/transports

This is a strong clue that MARA treats the firmware as a **modular runtime**, not a monolithic sketch.

### 3.2 Setup module order matters

The ordered manifest is defined in:
- `firmware/mcu/src/setup/SetupManifest.cpp`

Current order:
1. WiFi
2. OTA
3. Safety
4. Motors
5. Sensors
6. Transport
7. Telemetry

This order encodes the intended boot philosophy:
- networking/recovery first
- safety before actuators
- hardware before remote control surface
- telemetry only after providers exist

If startup bugs appear, this manifest order is one of the first places to inspect.

### 3.3 Real-time scheduling model

The firmware uses a mixed scheduling model:
- a dedicated **FreeRTOS control task** for the control loop
- cooperative/rate-limited loops in `loop()` for safety, telemetry, sensors, and host work

So MARA is not fully interrupt/task-driven and not fully cooperative either. It is a hybrid.

That means timing problems can come from:
- task scheduling / priority on the control loop
- loop-rate configuration drift
- transport or telemetry load impacting the cooperative side

---

## 4. Safety model

### 4.1 Setup location

Safety setup lives at:
- `firmware/mcu/src/setup/SetupSafety.cpp`

It configures a `ModeManager` with:
- host timeout
- motion timeout
- max linear/angular velocity
- optional estop / bypass / relay pins

It also registers two important callbacks:
- **stop callback**: normal stop path, calls motion stop and DC motor stop
- **emergency stop callback**: direct actuator shutdown path, including stepper stop

### 4.2 Why this matters

Safety is not just a CLI convention. It exists in firmware and has direct actuator shutdown semantics.

That means host-side arming/disarming only makes sense if it converges with firmware `ModeManager` behavior.

### 4.3 Current branch-local change

The current branch carries an uncommitted change in:
- `firmware/mcu/src/setup/SetupSafety.cpp`

Current diff:
- `host_timeout_ms` from `2000` -> `10000`

Interpretation:
- the branch is already experimenting with a more tolerant host watchdog
- this likely matters for TCP/WiFi or agent-driven control where timing is less deterministic than direct serial

This is a meaningful behavioral change, not cosmetic.

---

## 5. Feature-flagged firmware

The MCU firmware is heavily feature-flagged in:
- `firmware/mcu/platformio.ini`

Major preset profiles:
- `esp32_minimal`
- `esp32_motors`
- `esp32_sensors`
- `esp32_control`
- `esp32_full`

Flags control:
- transport availability
- actuator classes
- sensor classes
- control subsystems
- OTA / telemetry / heartbeat / logging / identity

### Practical consequence

When debugging behavior, never assume all subsystems exist.

A bug report about a missing capability may be caused by:
- the wrong environment
- a preset excluding the feature
- a generated config mismatch
- a runtime/client assumption that a feature exists

The build profile is part of the runtime truth.

---

## 6. Host architecture: what actually matters

The host package root is:
- `host/mara_host/`

The directories that matter most for behavior are:
- `cli/`
- `services/`
- `command/`
- `transport/`
- `telemetry/`
- `mcp/`
- `robot_layer/`
- `runtime/`
- `workflows/`

### 6.1 Practical layer model

The useful execution model is:

```text
Presentation:
  cli/, gui/

Application / orchestration:
  workflows/, runtime/

Business logic:
  services/

Protocol client:
  command/

Byte transport:
  transport/

Hardware target:
  firmware/mcu
```

This largely matches the existing architecture docs and seems real, not aspirational.

---

## 7. The host convergence point: services

The most important host packages for control are in:
- `host/mara_host/services/control/`

Examples:
- `state_service.py`
- `servo_service.py`
- `motor_service.py`
- `gpio_service.py`
- `stepper_service.py`
- `encoder_service.py`
- `imu_service.py`
- `ultrasonic_service.py`
- `pwm_service.py`

These services:
- expose domain operations
- track local state/config where appropriate
- call the underlying client with reliable commands
- return `ServiceResult` rather than raising UI-oriented exceptions

### Why they matter

If you are changing robot behavior from the host side, services are usually the safest place.

They are shared by:
- CLI contexts
- MCP runtime
- likely workflows and other operator surfaces

This reduces duplication and gives one place to enforce policy.

---

## 8. Connection and command path

### 8.1 Connection lifecycle

Primary connection logic is in:
- `host/mara_host/services/transport/connection_service.py`
- `host/mara_host/cli/context.py`

`ConnectionService` chooses the transport:
- serial
- TCP
- CAN
- MQTT listed as supported conceptually, though transport creation currently focuses on serial/TCP/CAN

`CLIContext` then builds on top of this by:
- connecting
- creating telemetry service
- starting telemetry
- auto-arming through `StateService`

### 8.2 The client chokepoint

The main client is:
- `host/mara_host/command/client.py`

This is the host-side coordinator for:
- handshake/version verification
- connection monitoring
- heartbeat loop
- reliable command sending
- binary telemetry parsing
- command routing through the commander

This file is one of the most critical in the entire repo.

### 8.3 Reliable vs streaming behavior

Per the architecture docs and client design, commands converge through the commander layer.

Conceptually there are two paths:
- **reliable commands** for setup/config/important operations
- **streaming commands** for higher-rate or less stateful control

This distinction is a major design feature and likely one source of subtle bugs if services accidentally choose the wrong command style.

---

## 9. Telemetry model

Telemetry lives across:
- `host/mara_host/services/telemetry/telemetry_service.py`
- `host/mara_host/telemetry/binary_parser.py`
- firmware telemetry modules/providers

### 9.1 Host-side view

The telemetry service:
- subscribes to client/bus events
- exposes callbacks for IMU, encoder, state, etc.
- maintains snapshots / latest readings

### 9.2 Binary protocol shape

The binary parser expects a sectioned telemetry frame with:
- version
- sequence
- timestamp
- section count
- section payloads

Known parsed sections include:
- IMU
- ultrasonic
- lidar
- encoder0
- stepper0
- dc_motor0
- control signals
- observers
- control slots

### 9.3 Important consequence

Telemetry freshness is a first-class concern, especially in the MCP runtime.

The runtime stores values with freshness/staleness windows, which is exactly the right design for LLM/operator use, because it distinguishes:
- latest known value
- current trustworthy value
- stale cached value

That design is stronger than just exposing raw last-seen telemetry.

---

## 10. MCP/HTTP runtime: the correct agent interface

For agent-driven control, the key files are:
- `host/mara_host/mcp/tool_schema.py`
- `host/mara_host/mcp/runtime.py`
- `host/mara_host/mcp/http_server.py`
- generated: `host/mara_host/mcp/_generated_http.py`

### 10.1 Single source of truth

`tool_schema.py` is the important source file.

It defines:
- tool names
- categories
- service bindings
- params
- whether arming is required
- response formatting
- custom handlers vs generated handlers

The HTTP routes are generated from this schema.

### 10.2 Why this matters

If an agent should be allowed to do something new, the clean place to model it is usually:
1. service method
2. schema entry in `tool_schema.py`
3. regenerate MCP/HTTP surface

This is much better than hand-adding ad hoc endpoints.

### 10.3 Current exposed capabilities

The currently visible tool surface includes at least:
- connect/disconnect/state/freshness/events/command stats
- arm/disarm/stop
- servo attach/set/center/detach
- motor set/stop
- gpio write/toggle/read
- stepper move/stop
- pwm set
- encoder read/reset
- imu read
- ultrasonic attach/read/detach
- robot-level move/home

This is enough to make the runtime a legitimate robot operator interface, not just a demo layer.

---

## 11. Robot layer: semantic control above raw actuators

Robot abstraction lives in:
- `host/mara_host/robot_layer/model.py`
- `host/mara_host/robot_layer/loader.py`
- `host/mara_host/robot_layer/service.py`
- `host/mara_host/robot_layer/context.py`

### 11.1 What it does

The robot layer maps:
- **semantic joint names**
- to **actuator types + actuator IDs**
- then delegates actual movement to the existing services

This is important because it creates a path from:
- raw hardware commands
- to named-joint robot motion
- to trajectories and higher-level control

### 11.2 Design quality

This is a good extension point because it does not bypass the underlying services.

That means semantic motion still inherits:
- service logic
- command tracking
- transport behavior
- safety expectations

### 11.3 Caveat

The robot layer depends on valid YAML robot models. If those are wrong, the semantic interface can look healthy while actuating the wrong hardware.

So robot-layer bugs may actually be configuration bugs.

---

## 12. Generated vs authoritative files

There are several generated or derived files in this repo. Treat them carefully.

### 12.1 Authoritative sources

Usually authoritative:
- `host/mara_host/mcp/tool_schema.py`
- `firmware/mcu/include/config/pins.json` or generator inputs (not the generated output)
- build/generation command source files
- service implementations
- runtime implementations
- firmware setup modules / command handlers

### 12.2 Generated outputs

Examples:
- `firmware/mcu/include/config/PinConfig.h`
- `host/mara_host/mcp/_generated_http.py`

Do not edit generated files unless you explicitly intend to break/regenerate workflow expectations.

---

## 13. Hardware truth currently visible from code

From generated pin config:
- `LED_STATUS = 2`
- `SERVO1_SIG = 18`
- `MOTOR_LEFT_IN1 = 12`
- `MOTOR_LEFT_IN2 = 13`
- `MOTOR_LEFT_PWM = 14`
- `ENC0_A = 32`
- `ENC0_B = 33`
- `ULTRA0_TRIG = 25`
- `ULTRA0_ECHO = 26`
- `STEPPER0_STEP = 19`
- `STEPPER0_DIR = 23`
- `STEPPER0_EN = 27`

Use these as code-truth unless the generator inputs say otherwise.

---

## 14. Current live-control observation

From the running environment at the time of writing:
- a MARA HTTP runtime was already running on port `8000`
- it was configured to connect over TCP to `10.0.0.60:3333`
- schema exposure worked
- live state/read paths appeared inconsistent (`already_connected` vs `not_connected` / internal errors)

### Interpretation

The agent-facing interface is real and present, but the live runtime/connection state may currently be unhealthy or internally inconsistent.

This suggests future debugging should inspect:
- `mcp/runtime.py` connection state handling
- `CLIContext.connect()` side effects and telemetry startup
- TCP transport stability
- whether the HTTP server holds a stale runtime context after connection loss
- whether `already_connected` is too weak a condition in `runtime.connect()`

This is one of the most important practical debugging areas for agent control.

---

## 15. Best edit points by task type

### If you want to change hardware behavior
Edit:
- firmware setup modules
- firmware command handlers
- firmware control/motor/sensor modules

### If you want to change host-side control semantics
Edit:
- `host/mara_host/services/control/*`

### If you want to expose a new capability to agents
Edit:
- `host/mara_host/services/...`
- `host/mara_host/mcp/tool_schema.py`
- regenerate generated HTTP/MCP outputs

### If you want to change connection behavior
Edit:
- `host/mara_host/services/transport/connection_service.py`
- `host/mara_host/cli/context.py`
- `host/mara_host/command/client.py`
- transport implementation files

### If you want to change named-joint robot behavior
Edit:
- `host/mara_host/robot_layer/*`
- robot YAML configs

### If you want to change firmware composition or boot sequence
Edit:
- `firmware/mcu/src/setup/SetupManifest.cpp`
- `firmware/mcu/src/main.cpp`

---

## 16. Where the repo feels strongest

The strongest design choices appear to be:

1. **Shared service layer** between CLI and agent interfaces
2. **Explicit setup-module boot ordering** in firmware
3. **Feature-flagged build profiles** for different robot capabilities
4. **Freshness-aware runtime state** for agent/operator interfaces
5. **Semantic robot layer built on top of services, not beside them**

These make the system relatively navigable despite its breadth.

---

## 17. Where the repo likely deserves extra caution

Areas that look most likely to hide subtle bugs:

1. **connection/runtime state coherence**
   - especially MCP runtime vs actual transport health
2. **arming/safety semantics across layers**
   - CLI, services, MCP runtime, and firmware ModeManager must agree
3. **generated-file drift**
   - schema or pin truth may diverge from generated outputs if regeneration is skipped
4. **feature-flag assumptions**
   - host code may assume subsystems exist when build flags exclude them
5. **hybrid timing model**
   - FreeRTOS control + cooperative loop makes timing bugs possible

---

## 18. Deeper findings after trace and runtime review

After a deeper pass, several concrete findings are now clear.

### 18.1 The command path is structurally sound
A representative command path now looks like this:

```text
HTTP route / CLI command
  -> runtime or CLIContext
  -> control service
  -> MaraClient.send_reliable(...)
  -> ReliableCommander
  -> transport
  -> firmware CommandRegistry
  -> specific handler
  -> ACK JSON
  -> client ACK resolver
  -> service result
```

This is a healthy overall design because:
- service logic is centralized
- wire/retry behavior is centralized
- MCU handler dispatch is centralized
- ACK semantics are centralized

### 18.2 Servo commands have a better real-time story than raw GPIO
Servo motion is especially interesting:
- host sends `CMD_SERVO_SET_ANGLE`
- MCU handler checks motion permission
- MCU stores a servo intent into `IntentBuffer`
- control task consumes it at deterministic loop boundaries
- motion manager / servo manager applies it

That means servo motion is designed to avoid command-burst jitter.

### 18.3 There are really two overlapping control systems
The firmware contains:

1. **practical motion control path**
   - motion controller
   - DC velocity PID loop in `LoopControl.cpp`
   - encoder feedback
   - direct actuator managers

2. **generalized control fabric**
   - `SignalBus`
   - `ObserverManager`
   - `ControlKernel`
   - `ControlModule`

This is powerful, but it means edits must respect which layer is actually in charge for a given behavior.

### 18.4 The HTTP runtime inconsistency is explainable from code
Observed behavior:
- `/connect` can report `already_connected`
- `/state` can simultaneously report `not_connected`

Code reason:
- `MaraRuntime.connect()` treats `self._ctx is not None` as already connected
- `runtime.is_connected` additionally requires `self._ctx.is_connected`
- `CLIContext.is_connected` depends on `_client is not None`

So stale `_ctx` objects can make the runtime claim two different truths at once.

This is not just a vague transport problem. It is a lifecycle/coherence bug in the MCP runtime.

### 18.5 Some service contracts are thinner than the MCU ACK payloads
Example:
- firmware GPIO read handler returns `value`
- host `GpioService.read()` currently returns success without surfacing that read value cleanly

This suggests some host services are losing useful information from ACK payloads, which weakens the HTTP layer.

### 18.6 Servo attach semantics do not fully line up across layers
The host servo service models attach as pin/channel-configurable.

But current firmware `ServoHandler` maps `servo_id` to fixed pin definitions from `PinConfig.h`.

So the host contract currently appears more flexible than the firmware implementation really is.

---

## 19. Recommended next exploration targets

To deepen this map even further, the next most valuable investigations are:

1. inspect `ReliableCommander` retry/backoff semantics in more detail
2. trace telemetry provider registration from firmware section IDs to host parser/freshness storage
3. reconcile service return payloads with MCU ACK payloads for read-style commands
4. reconcile servo attach semantics between host and firmware
5. patch MCP runtime lifecycle handling and re-test live HTTP behavior

---

## 20. Short operational summary

If you only remember one thing, remember this:

> MARA is best understood as a layered robot platform where **services are the host-side center of gravity** and **setup modules are the firmware-side center of gravity**.

For safe edits:
- respect service boundaries on host
- respect setup ordering and safety semantics on firmware
- treat generated files as outputs, not primary edit targets
- verify feature flags before assuming capability

---

## 21. Branch context

This map was written while exploring:
- branch: `openclaw/workbench`

At the time of writing, the branch also contained an uncommitted change to:
- `firmware/mcu/src/setup/SetupSafety.cpp`

That change increases host watchdog timeout from 2s to 10s.
