# OpenClaw Edit Guide for MARA

This is the tactical companion to `OPENCLAW_SYSTEM_MAP.md`.

Use this when the question is not "how is the system shaped?" but:

- where do I edit to change behavior?
- what path does a command actually take?
- what are the dangerous mismatch zones?

---

## 1. End-to-end command trace

This section traces a representative command through the full stack.

### 1.1 Example A: MCP HTTP GPIO read/write path

#### Agent-facing entry
HTTP endpoint generated in:
- `host/mara_host/mcp/_generated_http.py`

Example route:
- `POST /gpio/write`
- `POST /gpio/read`

The route logic is conceptually:

```text
HTTP request
  -> runtime.ensure_connected() or ensure_armed()
  -> runtime.gpio_service.write(...) / read(...)
  -> runtime.record_command(...)
  -> JSON HTTP response
```

#### Runtime layer
Runtime object:
- `host/mara_host/mcp/runtime.py`

It exposes:
- `gpio_service` property -> delegated to `CLIContext.gpio_service`
- `ensure_connected()` / `ensure_armed()` for lifecycle and state gating

#### Service layer
GPIO service:
- `host/mara_host/services/control/gpio_service.py`

Methods:
- `write(channel, value)` -> sends `CMD_GPIO_WRITE`
- `read(channel)` -> sends `CMD_GPIO_READ`
- `toggle(channel)` -> sends `CMD_GPIO_TOGGLE`
- `register(...)` -> sends `CMD_GPIO_REGISTER_CHANNEL`

Important behavior:
- service uses `client.send_reliable(...)`
- local service state is updated on successful ACK
- **read path currently discards returned MCU value** and only returns `{"channel": channel}` locally

That means the service contract is weaker than the MCU ACK payload. This is likely worth fixing.

#### Client / reliable command layer
Client:
- `host/mara_host/command/client.py`

Flow:
1. service calls `client.send_reliable("CMD_GPIO_WRITE", payload)`
2. client delegates to `ReliableCommander.send(...)`
3. command serialized to JSON frame by `_send_json_cmd_internal(...)`
4. frame written by active transport
5. MCU later replies with ACK JSON including `src="mcu"`, `ok`, `seq`
6. `MaraClient` ACK path publishes result back into `ReliableCommander`
7. waiting future resolves `(ok, error)` back to service

Important detail:
- ACK detection is generic: if JSON has `src == "mcu"` and `ok`, it is treated as an ACK
- state changes are also published onto the bus via `state.changed`

#### Transport layer
For the currently running HTTP runtime, transport is TCP:
- `host/mara_host/services/transport/connection_service.py`
- `host/mara_host/transport/tcp_transport.py`

Path:
```text
send_reliable
  -> MaraClient._send_frame(...)
  -> AsyncTcpTransport.send_bytes(...)
  -> TCP socket to MCU WiFi server
```

#### MCU ingress
Firmware command ingress:
- `firmware/mcu/src/command/CommandRegistry.cpp`

Path:
1. transport/router emits `JSON_MESSAGE_RX`
2. `CommandRegistry::handleEvent()` calls `ctx_.mode.onHostHeartbeat(...)`
3. JSON decoded into `JsonMessage`
4. `seq` and `cmdType` loaded into `CommandContext`
5. handler registry or legacy handler dispatch occurs

#### MCU handler
GPIO handler:
- `firmware/mcu/src/command/handlers/GpioHandler.cpp`

For write:
- validates channel with `gpio_.hasChannel(ch)`
- applies `gpio_.write(ch, val)`
- sends ACK using `ctx.sendAck("CMD_GPIO_WRITE", ok, resp)`

For read:
- validates channel
- reads value
- sends ACK payload with `channel`, `value`

#### ACK return path
```text
MCU ctx.sendAck(...)
  -> router/transport
  -> host client receives JSON
  -> ACK detector resolves seq future
  -> service returns ServiceResult
  -> HTTP route returns JSON
```

### 1.2 Example B: MCP HTTP servo move path

#### HTTP layer
- `POST /servo/set` in generated HTTP routes

Route behavior:
- `await runtime.ensure_armed()`
- `await runtime.servo_service.set_angle(...)`

#### Service layer
Servo service:
- `host/mara_host/services/control/servo_service.py`

Method:
- `set_angle(servo_id, angle, duration_ms, request_ack=True)`

Behavior:
- clamp/inversion in host service
- sends `CMD_SERVO_SET_ANGLE`
- can use reliable or fire-and-forget mode
- updates local cached servo state on success

#### MCU handler
Servo handler:
- `firmware/mcu/src/command/handlers/ServoHandler.cpp`

Important semantics:
- movement requires `ctx.mode.canMove()` or it returns `not_armed`
- it marks motion activity via `ctx.mode.onMotionCommand(now_ms)`
- it writes into `IntentBuffer` when available instead of immediately twitching hardware

This is a major design point:
- **servo set is not necessarily applied directly inside the command handler**
- the handler records intent for deterministic consumption in the control task

#### Real-time application
Intent consumption happens in:
- `firmware/mcu/src/setup/SetupControlTask.cpp`

Path:
1. control task wakes on fixed rate
2. consumes latest servo intent
3. if `duration_ms == 0`, calls `ctx->servo->setAngle(...)`
4. else delegates interpolated motion to `ctx->motion->setServoTarget(...)`

This means the actuator boundary is:

```text
Command handler -> IntentBuffer -> control task -> actuator/motion manager
```

That is good architecture for jitter control.

---

## 2. Firmware-side control stack map

There are two overlapping control systems in the firmware.

### 2.1 Motion/actuator control path
This is the practical robot-actuation path:
- `MotionController`
- `DcMotorManager`
- `ServoManager`
- `StepperManager`
- encoder feedback in `runControlLoop(...)`

Important file:
- `firmware/mcu/src/loop/LoopControl.cpp`

Current explicit behavior there:
- encoder 0 ticks -> angular velocity estimate
- velocity estimate -> `dcMotor->updateVelocityPid(0, omega_rad_s, dt)`
- motion controller updated if mode allows motion

This is the bread-and-butter motion path.

### 2.2 Advanced control module path
This is the more general signal/control architecture:
- `SignalBus`
- `ObserverManager`
- `ControlKernel`
- `ControlModule`

Files:
- `firmware/mcu/include/control/SignalBus.h`
- `firmware/mcu/src/control/SignalBus.cpp`
- `firmware/mcu/include/control/Observer.h`
- `firmware/mcu/src/control/Observer.cpp`
- `firmware/mcu/include/control/ControlKernel.h`
- `firmware/mcu/src/control/ControlKernel.cpp`
- `firmware/mcu/src/module/ControlModule.cpp`

#### SignalBus
Purpose:
- shared signal memory for references, measurements, outputs, estimates
- supports ids, names, aliases, timestamps, rate limiting

Kinds:
- `REF`
- `MEAS`
- `OUT`
- `EST`

Meaning:
- controllers and observers are decoupled from raw sensor/actuator classes
- they interact through signal IDs

#### ObserverManager
Current real implementation is Luenberger-style observer slots.

Behavior:
- configured per slot with input/output/estimate mappings
- runs before controllers
- writes state estimates back to signal bus

Important nuance:
- host-side schema may speak in broader terms like Kalman/EKF
- firmware runtime appears to execute a more concrete observer core, often represented as Luenberger-form matrices

So some host abstractions are richer than the exact firmware primitive.

#### ControlKernel
Supports multiple controller slots.

Current key facts:
- max slots are bounded
- supports at least `PID` and `STATE_SPACE`
- each slot reads signals, computes output, writes signals
- `step(...)` is gated by `is_armed` / `is_active`

This means ControlKernel is a generalized control fabric, not just "PID for motors".

#### ControlModule
Purpose:
- own the signal bus, observer manager, and control kernel
- step them in the proper order
- export their telemetry

Order inside `ControlModule::loop(...)`:
1. compute dt
2. derive armed/active state from mode manager
3. **step observers first**
4. **step controllers second**

That order is exactly right for observer-based control.

---

## 3. Runtime inconsistency diagnosis

A real inconsistency was observed live:
- `POST /connect` returned `{"status":"already_connected"}`
- `GET /state` returned `{"error":"not_connected"}`

This is explainable directly from code.

### 3.1 Root cause
In `host/mara_host/mcp/runtime.py`:

```python
async def connect(self):
    async with self._lock:
        if self._ctx is not None:
            return {"status": "already_connected"}
```

But `runtime.is_connected` is:

```python
return self._ctx is not None and self._ctx.is_connected
```

And `CLIContext.is_connected` is:

```python
return self._client is not None
```

So there is a bad intermediate state where:
- `_ctx` still exists
- but `_ctx._client` is gone / unhealthy / not actually connected
- `/connect` only checks `_ctx is not None`
- `/state` checks `runtime.is_connected`, which additionally requires `_ctx.is_connected`

Result:
- **connect says already connected**
- **state says not connected**

That is a real logic bug in runtime lifecycle handling.

### 3.2 Most likely fix strategy
`MaraRuntime.connect()` should not treat non-`None` context as sufficient.

Safer logic would be something like:
- if `_ctx is not None and _ctx.is_connected`: return already_connected
- if `_ctx is not None and not _ctx.is_connected`: discard/rebuild context
- only then create fresh `CLIContext`

Additionally, exceptions during startup should probably clear `_ctx` before returning failure.

### 3.3 Why this matters
This bug can make the HTTP interface look alive while being functionally dead.

That is especially dangerous for agent control because it creates false confidence.

---

## 4. Other mismatches worth noting

### 4.1 Servo attach host/firmware parameter mismatch
Host service sends:
- `channel`

Firmware servo handler actually uses:
- `servo_id`
- and internally maps that ID to `Pins::SERVO1_SIG`

In `ServoHandler.cpp`, the payload field `channel` is not used for pin selection.

Implication:
- host API suggests arbitrary attach pin selection
- firmware currently behaves more like fixed servo-id-to-pin mapping

That is a semantic mismatch.

### 4.2 GPIO/encoder/IMU read services may under-return data
Example: `GpioService.read()` returns success but does not surface MCU `value`.

Implication:
- HTTP routes that rely on service `result.data` may fail to expose actual sensor/readback values clearly
- some routes may be reporting only `{ok, error, state}` instead of useful data

This likely contributes to the feeling that the HTTP interface is thinner than the underlying MCU ACKs.

### 4.3 CLI auto-arm side effect
`CLIContext.connect()` automatically:
- starts telemetry
- arms robot

That is convenient, but it also means "connect" is not a neutral lifecycle action.

Implication:
- some runtime or debugging behavior may be harder to reason about because connection implies partial activation semantics

---

## 5. Best edit points by objective

### Objective: Fix agent/runtime connection truthfulness
Edit first:
- `host/mara_host/mcp/runtime.py`
- possibly `host/mara_host/mcp/http_server.py`
- possibly `host/mara_host/cli/context.py`

### Objective: Make HTTP read endpoints return useful payloads
Edit first:
- `host/mara_host/services/control/gpio_service.py`
- `encoder_service.py`
- `imu_service.py`
- generated HTTP response shaping if needed

### Objective: Add a new agent-visible capability
Edit first:
- service implementation in `host/mara_host/services/...`
- `host/mara_host/mcp/tool_schema.py`
- regenerate `host/mara_host/mcp/_generated_http.py`

### Objective: Add/modify low-level command support
Edit first:
- `host/mara_host/config/commands.json` or schema sources
- host command helpers / generated command code
- firmware command decoders/handlers/registry

### Objective: Change motion safety semantics
Edit first:
- `firmware/mcu/src/setup/SetupSafety.cpp`
- `command/ModeManager.*`
- motion/actuator stop callbacks

### Objective: Improve deterministic actuation behavior
Edit first:
- `firmware/mcu/src/setup/SetupControlTask.cpp`
- `core/IntentBuffer.*`
- actuator managers / motion controller

### Objective: Change control theory features
Edit first:
- `firmware/mcu/src/control/*`
- `firmware/mcu/src/module/ControlModule.cpp`
- host `services/control/controller_service.py`
- host `control/` upload/design helpers

---

## 6. Fast mental model: where to look first

If the problem is...

### "The API says it worked but the robot didn’t move"
Look at:
- runtime connection truth
- state/arming checks
- intent buffer path
- control task consumption
- motion manager / servo manager

### "The robot moved wrong"
Look at:
- robot layer mapping
- service clamping/inversion
- firmware handler semantics
- pin config / feature flags

### "Telemetry looks stale or wrong"
Look at:
- `TelemetryService`
- binary parser section mapping
- runtime freshness store
- telemetry provider registration in firmware

### "Feature exists in host but not on hardware"
Look at:
- `platformio.ini`
- firmware feature flags
- device manifest / capabilities
- generated schema assumptions

---

## 7. Recommended technical next steps

Highest-value follow-ups for this branch:

1. fix MCP runtime connect/disconnect state coherence
2. improve service read methods so returned values propagate cleanly
3. reconcile servo attach semantics (host-configurable pin vs firmware fixed pin mapping)
4. add a lightweight runtime self-check endpoint that verifies:
   - transport connected
   - telemetry alive
   - ACK round-trip working
   - state freshness acceptable

Those four would significantly improve trust in agent control.
