// include/core/IntentBuffer.h
// Thread-safe intent storage for command-to-actuator separation
//
// =============================================================================
// INTENT CONTRACT
// =============================================================================
//
// PURPOSE:
//   Decouples command handlers (async, variable rate) from control loop
//   (deterministic, fixed rate). Commands set "intents" which the control
//   loop consumes at its next tick.
//
// PRODUCERS (Command Handlers):
//   - MotionHandler     → setVelocityIntent()     via CMD_SET_VEL
//   - ServoHandler      → setServoIntent()        via CMD_SERVO_SET_ANGLE
//   - DcMotorHandler    → setDcMotorIntent()      via CMD_DC_SET_SPEED
//   - StepperHandler    → setStepperIntent()      via CMD_STEPPER_MOVE_REL
//   - ControlHandler    → queueSignalIntent()     via CMD_CTRL_SIGNAL_SET
//
// CONSUMER (Control Loop - LoopControl.cpp / SetupControlTask.cpp):
//   - Runs at fixed rate (e.g., 100Hz)
//   - Calls consume*Intent() at start of each tick
//   - Applies consumed intents to actuators/signals
//   - Stale intents (not consumed) are overwritten by next command
//
// SEMANTICS:
//   - Velocity/Servo/DcMotor/Stepper: Latest-wins (single slot per ID)
//   - Signals: Ring buffer (16 slots), drop-oldest on overflow
//   - All intents carry timestamp for staleness detection
//
// EXPIRY:
//   - Intents do NOT auto-expire - consumer must check timestamp if needed
//   - ModeManager enforces motion command timeout (default 2s)
//   - On ESTOP/disarm, clearAll() is called to drop pending intents
//
// OVERRIDE BEHAVIOR:
//   - ESTOP:      clearAll() + immediate motor stop
//   - STOP:       setVelocityIntent(0, 0, now) - zero velocity intent
//   - DISARM:     clearAll() + transition to IDLE
//   - DEACTIVATE: clearAll() + transition to ARMED
//
// THREAD SAFETY:
//   - All methods protected by spinlock (CriticalSection)
//   - Safe to call from any task/core
//   - Keep critical sections short (< 10μs)
//
// WHAT BYPASSES INTENTS (direct actuator calls allowed):
//   - Configuration: attach/detach, PID gains, enable/disable
//   - Safety overrides: ESTOP (immediate motor stop)
//   - Debug/diagnostic: motor mapping queries
//
// ENFORCEMENT:
//   Handlers MUST use intents for any continuous motion command.
//   Direct calls are only for configuration, safety, or diagnostics.
//   See ServiceContext.h for full coupling rules.
//
// =============================================================================

#pragma once

#include <cstdint>
#include "core/CriticalSection.h"
#include "core/RealTimeContract.h"

namespace mara {

// =============================================================================
// Intent Structs
// =============================================================================

/// Velocity intent from SET_VEL commands
struct VelocityIntent {
    float vx = 0.0f;
    float omega = 0.0f;
    uint32_t timestamp_ms = 0;
    bool pending = false;
};

/// Servo intent from SERVO_SET_ANGLE commands
struct ServoIntent {
    uint8_t id = 0;
    float angle_deg = 0.0f;
    uint32_t duration_ms = 0;
    uint32_t timestamp_ms = 0;
    bool pending = false;
};

/// DC Motor intent from DC_SET_SPEED commands
struct DcMotorIntent {
    uint8_t id = 0;
    float speed = 0.0f;
    uint32_t timestamp_ms = 0;
    bool pending = false;
};

/// Stepper intent from STEPPER_MOVE_REL commands
struct StepperIntent {
    int motor_id = 0;
    int steps = 0;
    float speed_steps_s = 0.0f;
    uint32_t timestamp_ms = 0;
    bool pending = false;
};

/// Signal set intent from CTRL_SIGNAL_SET commands
struct SignalIntent {
    uint16_t id = 0;
    float value = 0.0f;
    uint32_t timestamp_ms = 0;
};

// =============================================================================
// IntentBuffer Class
// =============================================================================

/// Thread-safe buffer for command intents
/// Uses spinlock for ESP32 multi-core safety (matches SignalBus pattern)
class IntentBuffer {
public:
    static constexpr uint8_t MAX_SERVO_INTENTS = 4;
    static constexpr uint8_t MAX_DC_MOTOR_INTENTS = 4;
    static constexpr uint8_t MAX_STEPPER_INTENTS = 4;
    static constexpr uint8_t MAX_SIGNAL_INTENTS = 16;

    IntentBuffer() {
        initSpinlock(lock_);
    }

    // -------------------------------------------------------------------------
    // Velocity Intent (single, latest-wins)
    // -------------------------------------------------------------------------

    /// Set velocity intent (called from command handler)
    void setVelocityIntent(float vx, float omega, uint32_t now_ms);

    /// Consume velocity intent (called from control task)
    /// Returns true if there was a pending intent
    RT_SAFE bool consumeVelocityIntent(VelocityIntent& out);

    // -------------------------------------------------------------------------
    // Servo Intent (by id)
    // -------------------------------------------------------------------------

    /// Set servo intent (called from command handler)
    void setServoIntent(uint8_t id, float angle, uint32_t dur_ms, uint32_t now_ms);

    /// Consume servo intent (called from control task)
    RT_SAFE bool consumeServoIntent(uint8_t id, ServoIntent& out);

    // -------------------------------------------------------------------------
    // DC Motor Intent (by id)
    // -------------------------------------------------------------------------

    /// Set DC motor intent
    void setDcMotorIntent(uint8_t id, float speed, uint32_t now_ms);

    /// Consume DC motor intent
    RT_SAFE bool consumeDcMotorIntent(uint8_t id, DcMotorIntent& out);

    // -------------------------------------------------------------------------
    // Stepper Intent (by id)
    // -------------------------------------------------------------------------

    /// Set stepper intent
    void setStepperIntent(int id, int steps, float speed, uint32_t now_ms);

    /// Consume stepper intent
    RT_SAFE bool consumeStepperIntent(int id, StepperIntent& out);

    // -------------------------------------------------------------------------
    // Signal Intent (ring buffer)
    // -------------------------------------------------------------------------

    /// Queue a signal set intent
    void queueSignalIntent(uint16_t id, float value, uint32_t now_ms);

    /// Consume next signal intent from queue
    /// Returns true if there was a pending intent
    RT_SAFE bool consumeSignalIntent(SignalIntent& out);

    /// Get number of pending signal intents
    RT_SAFE uint8_t pendingSignalCount() const;

    // -------------------------------------------------------------------------
    // Utility
    // -------------------------------------------------------------------------

    /// Clear all pending intents (e.g., on ESTOP)
    void clearAll();

private:
    mutable SpinlockType lock_ = MCU_SPINLOCK_INIT;

    // Storage
    VelocityIntent velocity_;
    ServoIntent servos_[MAX_SERVO_INTENTS];
    DcMotorIntent dcMotors_[MAX_DC_MOTOR_INTENTS];
    StepperIntent steppers_[MAX_STEPPER_INTENTS];

    // Signal ring buffer
    SignalIntent signalRing_[MAX_SIGNAL_INTENTS];
    uint8_t signalHead_ = 0;  // Write position
    uint8_t signalTail_ = 0;  // Read position
};

} // namespace mara
