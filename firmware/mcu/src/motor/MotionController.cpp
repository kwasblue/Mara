// src/core/MotionController.cpp
#include "motor/MotionController.h"
#include "motor/StepperManager.h"
#include "motor/DcMotorManager.h"
#include "motor/ServoManager.h"
#include "core/Debug.h"

MotionController::MotionController(DcMotorManager& motors,
                                   uint8_t leftMotorId,
                                   uint8_t rightMotorId,
                                   float wheelBase,
                                   float maxLinear,
                                   float maxAngular,
                                   ServoManager*  servoMgr,
                                   StepperManager* stepperMgr)
    : motors_(motors),
      servoMgr_(servoMgr),
      stepperMgr_(stepperMgr),
      leftId_(leftMotorId),
      rightId_(rightMotorId),
      wheelBase_(wheelBase),
      maxLinear_(maxLinear),
      maxAngular_(maxAngular),
      baseEnabled_(false)   // 🔹 start with base control OFF
{
    // init servo state
    for (uint8_t i = 0; i < ESP_MAX_SERVOS; ++i) {
        servoCurrent_[i]    = 0.0f;
        servoStart_[i]      = 0.0f;
        servoTarget_[i]     = 0.0f;
        servoStartMs_[i]    = 0;
        servoDurationMs_[i] = 0;
        servoActive_[i]     = false;
    }
}

// ===== Differential drive =====

void MotionController::setVelocity(float vx, float omega) {
    if (vx >  maxLinear_)  vx =  maxLinear_;
    if (vx < -maxLinear_)  vx = -maxLinear_;
    if (omega >  maxAngular_) omega =  maxAngular_;
    if (omega < -maxAngular_) omega = -maxAngular_;

    vxRef_    = vx;
    omegaRef_ = omega;

    // Optional: automatically enable base control when you first use it
    // baseEnabled_ = true;
}

void MotionController::stop() {
    vxRef_    = 0.0f;
    omegaRef_ = 0.0f;

    // Still force motors to stop regardless of baseEnabled_
    motors_.setSpeed(leftId_,  0.0f);
    motors_.setSpeed(rightId_, 0.0f);
}

float MotionController::vx() const {
    return vxRef_;
}

float MotionController::omega() const {
    return omegaRef_;
}

void MotionController::setAccelLimits(float maxLinAccel, float maxAngAccel) {
    maxLinAccel_ = maxLinAccel;
    maxAngAccel_ = maxAngAccel;
}

// NEW: enable/disable base control from outside
void MotionController::setBaseEnabled(bool enabled) {
    baseEnabled_ = enabled;
    DBG_PRINTF("[MotionController] baseEnabled=%d\n", (int)enabled);
    if (!enabled) {
        // When disabling, ensure motors are stopped
        motors_.setSpeed(leftId_,  0.0f);
        motors_.setSpeed(rightId_, 0.0f);
    }
}

// ===== Servo interface =====

void MotionController::setServoTarget(uint8_t servoId,
                                      float angleDeg,
                                      uint32_t durationMs) {
    if (!servoMgr_) return;
    if (servoId >= ESP_MAX_SERVOS) return;

    if (durationMs == 0) {
        // Immediate move: no trajectory, just write the angle now.
        servoCurrent_[servoId] = angleDeg;
        servoActive_[servoId]  = false;
        DBG_PRINTF("[MotionController] immediate servo id=%u angle=%.1f\n",
                   servoId, angleDeg);
        servoMgr_->setAngle(servoId, angleDeg);
        return;
    }

    // Schedule an interpolated move
    servoActive_[servoId]     = true;
    servoStart_[servoId]      = servoCurrent_[servoId];
    servoTarget_[servoId]     = angleDeg;
    servoStartMs_[servoId]    = now_ms();
    servoDurationMs_[servoId] = durationMs;

    DBG_PRINTF("[MotionController] servo id=%u target=%.1f dur=%lu ms (start=%.1f)\n",
               servoId, angleDeg, (unsigned long)durationMs, servoStart_[servoId]);
}

void MotionController::setServoImmediate(uint8_t servoId, float angleDeg) {
    setServoTarget(servoId, angleDeg, 0);
}

// ===== Stepper interface =====

void MotionController::moveStepperRelative(int motorId,
                                           int steps,
                                           float speedStepsPerSec) {
    if (!stepperMgr_) {
        DBG_PRINTF("[MotionController] moveStepperRelative: no stepperMgr (id=%d)\n",
                   motorId);
        return;
    }
    stepperMgr_->moveRelative(motorId, steps, speedStepsPerSec);
}

void MotionController::enableStepper(int motorId, bool enabled) {
    if (!stepperMgr_) {
        DBG_PRINTF("[MotionController] enableStepper: no stepperMgr (id=%d)\n",
                   motorId);
        return;
    }
    stepperMgr_->setEnabled(motorId, enabled);
}

// ===== Main update =====

void MotionController::update(float dt) {
    // --- 1) Base velocity / motor control ---
    if (baseEnabled_) {
        // Ramp vxCmd_ toward vxRef_
        float dvx = vxRef_ - vxCmd_;
        float maxDeltaVx = maxLinAccel_ * dt;
        if (dvx >  maxDeltaVx) dvx =  maxDeltaVx;
        if (dvx < -maxDeltaVx) dvx = -maxDeltaVx;
        vxCmd_ += dvx;

        // Ramp omegaCmd_ toward omegaRef_
        float domega = omegaRef_ - omegaCmd_;
        float maxDeltaOmega = maxAngAccel_ * dt;
        if (domega >  maxDeltaOmega) domega =  maxDeltaOmega;
        if (domega < -maxDeltaOmega) domega = -maxDeltaOmega;
        omegaCmd_ += domega;

        // Convert (vxCmd_, omegaCmd_) -> left/right wheel speeds
        // v_left  = vx - (omega * wheelBase / 2)
        // v_right = vx + (omega * wheelBase / 2)
        float vLeft  = vxCmd_ - (omegaCmd_ * wheelBase_ * 0.5f);
        float vRight = vxCmd_ + (omegaCmd_ * wheelBase_ * 0.5f);

        // Normalize to [-1, 1] using maxLinear_ as scale
        float leftNorm  = 0.0f;
        float rightNorm = 0.0f;

        if (maxLinear_ > 0.0f) {
            leftNorm  = vLeft  / maxLinear_;
            rightNorm = vRight / maxLinear_;
        }

        // Clamp
        if (leftNorm  >  1.0f) leftNorm  =  1.0f;
        if (leftNorm  < -1.0f) leftNorm  = -1.0f;
        if (rightNorm >  1.0f) rightNorm =  1.0f;
        if (rightNorm < -1.0f) rightNorm = -1.0f;

        motors_.setSpeed(leftId_,  leftNorm);
        motors_.setSpeed(rightId_, rightNorm);
    }

    // --- 2) Servo interpolation (independent of base control) ---
    if (!servoMgr_) return;

    uint32_t now = now_ms();
    for (uint8_t id = 0; id < ESP_MAX_SERVOS; ++id) {
        if (!servoActive_[id]) continue;

        uint32_t elapsed = now - servoStartMs_[id];
        if (elapsed >= servoDurationMs_[id]) {
            // Final position
            servoCurrent_[id] = servoTarget_[id];
            servoMgr_->setAngle(id, servoCurrent_[id]);
            servoActive_[id] = false;
            DBG_PRINTF("[MotionController] servo id=%u done at %.1f\n",
                       id, servoCurrent_[id]);
        } else {
            float t = (float)elapsed / (float)servoDurationMs_[id];  // 0..1
            float angle = servoStart_[id] +
                          t * (servoTarget_[id] - servoStart_[id]);
            servoCurrent_[id] = angle;
            servoMgr_->setAngle(id, servoCurrent_[id]);
        }
    }
}
