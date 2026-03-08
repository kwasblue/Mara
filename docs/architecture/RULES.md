# MARA Architecture Rules

<div align="center">

**Architectural constraints and coupling rules**

*Enforced by tests and code review*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

</div>

## Core Principles

| # | Principle | Description |
|:--|:----------|:------------|
| 1 | **Single Source of Truth** | `tools/schema/` owns all protocol definitions |
| 2 | **Layer Isolation** | Lower layers must not depend on higher layers |
| 3 | **Single Chokepoint** | ALL commands flow through `ReliableCommander` |
| 4 | **ServiceResult Pattern** | Services return results, APIs raise exceptions |
| 5 | **Intent-Based Control** | Commands set intents, control loop consumes them |

---

## Host Python Layer Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. api/              Public user-facing API (TOP)                           │
│                       → Validation, exceptions                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  2. services/control/ Business logic layer                                   │
│                       → State tracking, ServiceResult                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  3. command/          Client and commander                                   │
│                       → All commands flow through ReliableCommander         │
├─────────────────────────────────────────────────────────────────────────────┤
│  4. core/             Core infrastructure                                    │
│                       → EventBus, protocol, modules                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  5. transport/        Transport layer (BOTTOM)                               │
│                       → Raw bytes, connection lifecycle                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer Import Rules

| Layer | May Import From | Must NOT Import From |
|:------|:----------------|:---------------------|
| `api/` | services, core | command, transport |
| `services/control/` | command, core | api, runtime |
| `command/` | core, transport | api, services |
| `core/` | transport | api, services, command |
| `transport/` | (none from mara_host) | All mara_host modules |

### Enforcement

These rules are enforced by `tests/test_architecture.py`:
- `TestTransportLayerBoundary` - transport isolation
- `TestCoreLayerBoundary` - core isolation
- `TestInternalModulesHaveAll` - explicit exports

---

## Command Flow Rules

### Rule 1: All Commands Through Commander

Every command—reliable or streaming—flows through `ReliableCommander`:

```python
# CORRECT - all commands through commander
await self.commander.send()                            # Reliable
await self.commander.send_fire_and_forget(binary=True) # Streaming binary
await self.commander.send_fire_and_forget(binary=False) # Streaming JSON

# WRONG - bypassing commander
await self._transport.send_bytes(encoded_cmd)  # Breaks event emission
```

### Rule 2: API Routes Through Services

API layer validates and delegates to services:

```python
# CORRECT
class GPIO:
    async def write(self, channel: int, value: int) -> None:
        if not self.is_registered(channel):
            raise ValueError(f"Channel {channel} not registered")
        result = await self._service.write(channel, value)
        if not result.ok:
            raise RuntimeError(result.error)

# WRONG - API calling client directly
class GPIO:
    async def write(self, channel: int, value: int) -> None:
        await self._client.cmd_gpio_write(channel=channel, value=value)
```

### Rule 3: Services Return ServiceResult

Services never raise exceptions; they return `ServiceResult`:

```python
# CORRECT
class MotionService:
    async def set_velocity(self, vx: float, omega: float) -> ServiceResult:
        ok, error = await self.client.send_stream(...)
        if ok:
            return ServiceResult.success(data={"vx": vx, "omega": omega})
        else:
            return ServiceResult.failure(error=error or "Failed")

# WRONG - service raising exceptions
class MotionService:
    async def set_velocity(self, vx: float, omega: float) -> None:
        if error:
            raise RuntimeError("Failed")  # ← Should return ServiceResult
```

---

## MCU Firmware Coupling Rules

These rules govern how firmware components interact.

### Data Flow

```
Command → Handler → IntentBuffer → ControlLoop → SignalBus → Actuator
                                                     ↓
                                               Telemetry (read-only)
```

### Rule 1: Handlers → Intents (write-only)

Command handlers set intents via IntentBuffer. They do **NOT**:
- Directly control actuators
- Read sensor values
- Modify SignalBus directly

```cpp
// CORRECT
intents->setVelocityIntent(vx, omega, now_ms);

// WRONG - bypasses control loop
dcMotor->setSpeed(0, speed);
```

### Rule 2: Control Loop → Actuators

The control loop:
- Consumes intents at deterministic rate (100Hz)
- Applies control algorithms (PID, state-space)
- Writes outputs to SignalBus and actuators
- Runs on dedicated FreeRTOS task (Core 1)

```cpp
// Control loop consumes intents
VelocityIntent vel;
if (intents->consumeVelocityIntent(vel)) {
    motion->setVelocity(vel.vx, vel.omega);
}
```

### Rule 3: Telemetry → Signals (read-only snapshots)

Telemetry:
- Reads SignalBus snapshots (thread-safe)
- Does NOT compute control logic
- Does NOT modify signals

```cpp
// CORRECT - read-only snapshot
SignalSnapshot snaps[16];
size_t n = signals.snapshot(snaps, 16);

// WRONG - telemetry modifying signals
signals.set(SIGNAL_ID, value);  // Don't do this
```

### Rule 4: Safety → Mode (gate all operations)

ModeManager is the single source of truth for robot state:
- All safety checks go through ModeManager
- IntentBuffer cleared on ESTOP/disarm
- Motion commands gated by `mode.canMove()`

```cpp
// Always check mode before motion
if (mode.canMove()) {
    intents->setVelocityIntent(vx, omega, now_ms);
}
```

---

## ServiceContext Tiers (MCU)

Services in ServiceContext are organized by initialization order:

| Tier | Category | Dependencies | Examples |
|:-----|:---------|:-------------|:---------|
| 0 | HAL | None | IGpio, IPwm, II2c |
| 1 | Core | HAL | EventBus, ModeManager, IntentBuffer |
| 2 | Motors | Core + HAL | DcMotorManager, ServoManager |
| 3 | Sensors | Core + HAL | EncoderManager, ImuManager |
| 4 | Communication | Core | Transport, CommandRegistry |
| 5 | Orchestration | All | ControlModule, MCUHost |

**Rule: Initialize in tier order**

```cpp
// CORRECT
initHal();           // Tier 0
initCore();          // Tier 1
initMotors();        // Tier 2

// WRONG - violates initialization order
initMotors();        // Tier 2 - depends on uninitialized HAL
initHal();           // Tier 0 - too late!
```

---

## Naming Conventions

| Suffix | Responsibility | Example |
|:-------|:---------------|:--------|
| `Service` | Business logic + state tracking | `MotionService`, `GpioService` |
| `Manager` | Hardware lifecycle and state (MCU) | `DcMotorManager`, `EncoderManager` |
| `Handler` | Command processing, no business logic | `MotionHandler`, `SafetyHandler` |
| `Module` | Runtime lifecycle (setup/loop) | `TelemetryModule`, `ControlModule` |
| `Registry` | Registration and lookup only | `HandlerRegistry`, `SensorRegistry` |
| `Controller` | Control algorithms | `MotionController`, `PIDController` |
| `Commander` | Command dispatch and tracking | `ReliableCommander` |

---

## Generated vs Manual Code

| Category | Edit? | Location | Generator |
|:---------|:------|:---------|:----------|
| Protocol definitions | Yes | `tools/schema/` | - |
| Command definitions | No | `config/command_defs.py` | `gen_commands.py` |
| Binary commands | No | `command/binary_commands.py` | `gen_binary_commands.py` |
| Telemetry sections | No | `telemetry/telemetry_sections.py` | `gen_telemetry.py` |
| C++ headers | No | `firmware/mcu/include/config/*.h` | Various generators |

**Rule: Never edit generated files**

```bash
# CORRECT - edit source, regenerate
vim host/mara_host/tools/schema/commands/_motion.py
mara generate all

# WRONG - editing generated file
vim host/mara_host/config/command_defs.py  # Will be overwritten!
```

---

## Real-Time Safety (MCU)

### Forbidden in Control Loop

| Operation | Why Forbidden | Alternative |
|:----------|:--------------|:------------|
| `new`/`delete` | Heap fragmentation | Pre-allocate at setup |
| `std::vector::push_back` | May reallocate | Fixed-size arrays |
| `std::string` | Heap-backed | `const char*` literals |
| `JsonDocument` | Allocates | Pre-parsed config |
| `Serial.print` | Unbounded I/O | Deferred logging |

### RT_SAFE Annotations

```cpp
// Safe for control loop - O(1), no allocation
RT_SAFE bool SignalBus::get(uint16_t id, float& out) const;

// NOT safe for control loop - may allocate
RT_UNSAFE void sendTelemetry();
```

---

## Thread Safety

### SignalBus Access

| Method | Thread Safety | Use Case |
|:-------|:--------------|:---------|
| `get()`, `set()` | Safe (spinlock) | Single-signal access |
| `snapshot()` | Safe (spinlock) | Bulk read for telemetry |
| `all()` | NOT SAFE | Setup-time only |
| `define()`, `clear()` | NOT SAFE | Setup-time only |

### Transport Layer

```python
# Transport uses asyncio.Lock for coordination
async def send_bytes(self, data: bytes) -> None:
    async with self._async_lock:  # No thread overhead for async callers
        await loop.run_in_executor(self._write_executor, self._send_bytes_sync, data)
```

---

## Summary Checklist

Before adding new code, verify:

- [ ] Layer imports follow hierarchy (use `test_architecture.py`)
- [ ] API validates and routes to services
- [ ] Services return `ServiceResult`, not exceptions
- [ ] Commands flow through `ReliableCommander`
- [ ] Generated files are not manually edited
- [ ] Command handlers only set intents, not direct actuation
- [ ] Control loop code is RT_SAFE (no allocation)
- [ ] Naming follows conventions

---

<div align="center">

*These rules ensure consistency across the codebase*

</div>
