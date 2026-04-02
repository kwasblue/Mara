// src/core/IntentBuffer.cpp
// Thread-safe intent buffer implementation

#include "core/IntentBuffer.h"
#include "core/CriticalSection.h"

namespace mara {

// =============================================================================
// Velocity Intent
// =============================================================================

void IntentBuffer::setVelocityIntent(float vx, float omega, uint32_t now_ms) {
    CriticalSection lock(lock_);
    velocity_.vx = vx;
    velocity_.omega = omega;
    velocity_.timestamp_ms = now_ms;
    velocity_.pending = true;
}

bool IntentBuffer::consumeVelocityIntent(VelocityIntent& out) {
    CriticalSection lock(lock_);
    if (!velocity_.pending) {
        return false;
    }
    out = velocity_;
    velocity_.pending = false;
    return true;
}

// =============================================================================
// Servo Intent
// =============================================================================

void IntentBuffer::setServoIntent(uint8_t id, float angle, uint32_t dur_ms, uint32_t now_ms) {
    if (id >= MAX_SERVO_INTENTS) return;

    CriticalSection lock(lock_);
    servos_[id].id = id;
    servos_[id].angle_deg = angle;
    servos_[id].duration_ms = dur_ms;
    servos_[id].timestamp_ms = now_ms;
    servos_[id].pending = true;
}

bool IntentBuffer::consumeServoIntent(uint8_t id, ServoIntent& out) {
    if (id >= MAX_SERVO_INTENTS) return false;

    CriticalSection lock(lock_);
    if (!servos_[id].pending) {
        return false;
    }
    out = servos_[id];
    servos_[id].pending = false;
    return true;
}

void IntentBuffer::setCompositeIntent(const CompositeIntent& intent) {
    CriticalSection lock(lock_);
    composite_ = intent;
    composite_.pending = true;
}

bool IntentBuffer::consumeCompositeIntent(CompositeIntent& out) {
    CriticalSection lock(lock_);
    if (!composite_.pending) {
        return false;
    }
    out = composite_;
    composite_.pending = false;
    return true;
}

// =============================================================================
// DC Motor Intent
// =============================================================================

void IntentBuffer::setDcMotorIntent(uint8_t id, float speed, uint32_t now_ms) {
    if (id >= MAX_DC_MOTOR_INTENTS) return;

    CriticalSection lock(lock_);
    dcMotors_[id].id = id;
    dcMotors_[id].speed = speed;
    dcMotors_[id].timestamp_ms = now_ms;
    dcMotors_[id].pending = true;
}

bool IntentBuffer::consumeDcMotorIntent(uint8_t id, DcMotorIntent& out) {
    if (id >= MAX_DC_MOTOR_INTENTS) return false;

    CriticalSection lock(lock_);
    if (!dcMotors_[id].pending) {
        return false;
    }
    out = dcMotors_[id];
    dcMotors_[id].pending = false;
    return true;
}

// =============================================================================
// Stepper Intent
// =============================================================================

void IntentBuffer::setStepperIntent(int id, int steps, float speed, uint32_t now_ms) {
    if (id < 0 || id >= MAX_STEPPER_INTENTS) return;

    CriticalSection lock(lock_);
    steppers_[id].motor_id = id;
    steppers_[id].steps = steps;
    steppers_[id].speed_steps_s = speed;
    steppers_[id].timestamp_ms = now_ms;
    steppers_[id].pending = true;
}

bool IntentBuffer::consumeStepperIntent(int id, StepperIntent& out) {
    if (id < 0 || id >= MAX_STEPPER_INTENTS) return false;

    CriticalSection lock(lock_);
    if (!steppers_[id].pending) {
        return false;
    }
    out = steppers_[id];
    steppers_[id].pending = false;
    return true;
}

// =============================================================================
// Signal Intent (Ring Buffer)
// =============================================================================

void IntentBuffer::queueSignalIntent(uint16_t id, float value, uint32_t now_ms) {
    CriticalSection lock(lock_);

    uint8_t next = (signalHead_ + 1) % MAX_SIGNAL_INTENTS;
    if (next == signalTail_) {
        // Ring buffer full - drop oldest entry and track overflow
        signalTail_ = (signalTail_ + 1) % MAX_SIGNAL_INTENTS;
        signal_overflow_count++;
    }

    signalRing_[signalHead_].id = id;
    signalRing_[signalHead_].value = value;
    signalRing_[signalHead_].timestamp_ms = now_ms;
    signalHead_ = next;
}

bool IntentBuffer::consumeSignalIntent(SignalIntent& out) {
    CriticalSection lock(lock_);

    if (signalHead_ == signalTail_) {
        return false;
    }

    out = signalRing_[signalTail_];
    signalTail_ = (signalTail_ + 1) % MAX_SIGNAL_INTENTS;
    return true;
}

uint8_t IntentBuffer::pendingSignalCount() const {
    CriticalSection lock(lock_);
    if (signalHead_ >= signalTail_) {
        return signalHead_ - signalTail_;
    }
    return MAX_SIGNAL_INTENTS - signalTail_ + signalHead_;
}

// =============================================================================
// Utility
// =============================================================================

void IntentBuffer::clearAll() {
    CriticalSection lock(lock_);

    velocity_.pending = false;

    for (uint8_t i = 0; i < MAX_SERVO_INTENTS; ++i) {
        servos_[i].pending = false;
    }
    composite_.pending = false;

    for (uint8_t i = 0; i < MAX_DC_MOTOR_INTENTS; ++i) {
        dcMotors_[i].pending = false;
    }

    for (uint8_t i = 0; i < MAX_STEPPER_INTENTS; ++i) {
        steppers_[i].pending = false;
    }

    signalHead_ = 0;
    signalTail_ = 0;
}

} // namespace mara
