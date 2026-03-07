# MARA Architecture Rules

This document defines the architectural constraints and coupling rules for the MARA platform. These rules are enforced by architecture tests and code review.

---

## Core Principles

1. **Single Source of Truth**: `platform_schema.py` owns all protocol definitions
2. **Layer Isolation**: Lower layers must not depend on higher layers
3. **Explicit Boundaries**: Public APIs are defined via `__all__` exports
4. **Intent-Based Control**: Commands set intents, control loop consumes them

---

## Host Python Layer Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│  1. api/           Public user-facing API (TOP)                 │
├─────────────────────────────────────────────────────────────────┤
│  2. runtime/       Runtime orchestration                        │
├─────────────────────────────────────────────────────────────────┤
│  3. command/       Client and command handling                  │
├─────────────────────────────────────────────────────────────────┤
│  4. motor/, sensor/, hw/    Host modules (domain logic)         │
├─────────────────────────────────────────────────────────────────┤
│  5. core/          Core infrastructure (events, protocol)       │
├─────────────────────────────────────────────────────────────────┤
│  6. transport/     Transport layer (BOTTOM)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Rules

| Layer | May Import From | Must Not Import From |
|-------|-----------------|----------------------|
| `api/` | All lower layers | - |
| `runtime/` | command, motor, sensor, hw, core, transport | api |
| `command/` | core, transport | api, runtime, motor, sensor, hw |
| `motor/`, `sensor/`, `hw/` | core, transport | api, runtime, command |
| `core/` | transport | api, runtime, command, motor, sensor, hw |
| `transport/` | (none from mara_host) | All mara_host modules |

### Enforcement

These rules are enforced by `tests/test_architecture.py`:
- `TestTransportLayerBoundary` - transport isolation
- `TestCoreLayerBoundary` - core isolation
- `TestInternalModulesHaveAll` - explicit exports

---

## MCU Firmware Coupling Rules

These rules are documented in `include/core/ServiceContext.h` and govern how firmware components interact.

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

### Rule 2: Control Loop → Actuators (consume intents, write signals)

The control loop:
- Consumes intents at deterministic rate (100Hz)
- Applies control algorithms (PID, state-space)
- Writes outputs to SignalBus and actuators
- Runs on dedicated FreeRTOS task (Core 1)

```cpp
// Control loop consumes intents
VelocityIntent vel;
if (intents->consumeVelocityIntent(vel)) {
    // Apply to motion controller
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

// WRONG - telemetry should not modify signals
signals.set(SIGNAL_ID, value);  // Don't do this from telemetry
```

### Rule 4: Sensors → Signals (write measurements)

Sensor managers:
- Write measurement signals to SignalBus
- Use consistent signal naming conventions
- Do NOT apply control logic

```cpp
// Sensor writes measurement
signals.set(SIG_WHEEL_VEL_LEFT, measuredVelocity);
```

### Rule 5: Safety → Mode (gate all operations)

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

## ServiceContext Tiers

Services in ServiceContext are organized by initialization order:

| Tier | Category | Dependencies | Examples |
|------|----------|--------------|----------|
| 0 | HAL | None | IGpio, IPwm, II2c |
| 1 | Core | HAL | EventBus, ModeManager, IntentBuffer |
| 2 | Motors | Core + HAL | DcMotorManager, ServoManager |
| 3 | Sensors | Core + HAL | EncoderManager, ImuManager |
| 4 | Communication | Core | Transport, CommandRegistry |
| 5 | Orchestration | All | ControlModule, MCUHost |

### Rule: Initialize in tier order

```cpp
// CORRECT - initialize in tier order
initHal();           // Tier 0
initCore();          // Tier 1
initMotors();        // Tier 2
initSensors();       // Tier 3
initCommunication(); // Tier 4
initOrchestration(); // Tier 5

// WRONG - violates initialization order
initMotors();        // Tier 2 - depends on uninitialized HAL
initHal();           // Tier 0 - too late!
```

---

## Module Naming Conventions

| Suffix | Responsibility | Example |
|--------|----------------|---------|
| `Manager` | Owns hardware lifecycle and state | `DcMotorManager`, `EncoderManager` |
| `Handler` | Processes commands, no business logic | `MotionHandler`, `SafetyHandler` |
| `Module` | Runtime lifecycle (setup/loop) | `TelemetryModule`, `ControlModule` |
| `Registry` | Registration and lookup only | `HandlerRegistry`, `SensorRegistry` |
| `Controller` | Control algorithms | `MotionController`, `PIDController` |

### Rule: Names match responsibility

```cpp
// CORRECT - Manager owns hardware
class DcMotorManager {
    bool attach(uint8_t id, int pin, ...);  // Hardware lifecycle
    bool setSpeed(uint8_t id, float speed); // Hardware state
};

// WRONG - Handler should not own business logic
class MotionHandler {
    void computePID(...);  // This belongs in Controller
};
```

---

## Generated vs Manual Code

| Category | Edit? | Location | Generator |
|----------|-------|----------|-----------|
| Protocol definitions | Yes | `platform_schema.py` | - |
| Command definitions | No | `config/command_defs.py` | `gen_commands.py` |
| Binary commands | No | `command/binary_commands.py` | `gen_binary_commands.py` |
| Telemetry sections | No | `telemetry/telemetry_sections.py` | `gen_telemetry.py` |
| C++ headers | No | `firmware/mcu/include/config/*.h` | Various generators |

### Rule: Never edit generated files

```bash
# CORRECT - edit source, regenerate
vim host/mara_host/tools/platform_schema.py
make generate

# WRONG - editing generated file
vim host/mara_host/config/command_defs.py  # Will be overwritten!
```

---

## Real-Time Safety (MCU)

### Forbidden in Control Loop

| Operation | Why Forbidden | Alternative |
|-----------|---------------|-------------|
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
|--------|--------------|----------|
| `get()`, `set()` | Safe (spinlock) | Single-signal access |
| `snapshot()` | Safe (spinlock) | Bulk read for telemetry |
| `all()` | NOT SAFE | Setup-time only |
| `define()`, `clear()` | NOT SAFE | Setup-time only |

### ModeManager Transitions

All state transitions use `portENTER_CRITICAL()` for atomicity.

---

## Summary Checklist

Before adding new code, verify:

- [ ] Layer imports follow hierarchy (use `test_architecture.py`)
- [ ] Internal modules define `__all__`
- [ ] Command handlers only set intents, not direct actuation
- [ ] Control loop code is RT_SAFE (no allocation)
- [ ] ServiceContext access follows tier dependencies
- [ ] Naming follows Manager/Handler/Module/Registry conventions
- [ ] Generated files are not manually edited
