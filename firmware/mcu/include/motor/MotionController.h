// include/core/MotionController.h
#pragma once

#include <Arduino.h>
#include "core/Clock.h"
#include "core/RealTimeContract.h"

class DcMotorManager;
class ServoManager;
class StepperManager;

// MotionController:
// - Drives a differential-drive base using DcMotorManager (vx, omega in SI units)
// - Smooths vx/omega over time (accel limits)
// - Optionally interpolates servo angles over time using ServoManager
// - Optionally commands steppers via StepperManager
class MotionController {
public:
    static constexpr uint8_t ESP_MAX_SERVOS = 1;  // bump when you add more

    MotionController(DcMotorManager& motors,
                     uint8_t leftMotorId,
                     uint8_t rightMotorId,
                     float wheelBase,
                     float maxLinear,
                     float maxAngular,
                     ServoManager*  servoMgr = nullptr,
                     StepperManager* stepperMgr = nullptr);

    virtual ~MotionController() = default;

    // ===== Differential drive velocity interface =====
    RT_SAFE virtual void setVelocity(float vx, float omega);
    RT_SAFE virtual void stop();

    RT_SAFE float vx() const;
    RT_SAFE float omega() const;

    void setAccelLimits(float maxLinAccel, float maxAngAccel);

    // Enable/disable base control (NEW)
    void setBaseEnabled(bool enabled);
    bool baseEnabled() const { return baseEnabled_; }

    // ===== Servo interface =====
    RT_SAFE void setServoTarget(uint8_t servoId,
                                float angleDeg,
                                uint32_t durationMs = 0);
    RT_SAFE void setServoImmediate(uint8_t servoId, float angleDeg);

    // ===== Stepper interface =====
    RT_SAFE void moveStepperRelative(int motorId,
                                     int steps,
                                     float speedStepsPerSec);
    RT_SAFE void enableStepper(int motorId, bool enabled);

    // ===== Main update (called every loop) =====
    RT_SAFE void update(float dt);

    // Clock injection for testability
    void setClock(mara::IClock* clk) { clock_ = clk; }

private:
    mara::IClock* clock_ = nullptr;

    /// Get current time from clock or fallback to system clock
    uint32_t now_ms() const {
        if (clock_) return clock_->millis();
        return mara::getSystemClock().millis();
    }

    // References
    DcMotorManager& motors_;
    ServoManager*   servoMgr_    = nullptr;
    StepperManager* stepperMgr_  = nullptr;

    // Base config
    uint8_t leftId_   = 0;
    uint8_t rightId_  = 1;
    float   wheelBase_ = 0.2f;
    float   maxLinear_ = 0.5f;
    float   maxAngular_ = 1.0f;

    // Velocity state
    float vxRef_      = 0.0f;
    float omegaRef_   = 0.0f;
    float vxCmd_      = 0.0f;
    float omegaCmd_   = 0.0f;
    float maxLinAccel_  = 1.0f;
    float maxAngAccel_  = 2.0f;

    // Whether MotionController is allowed to drive the base (NEW)
    bool baseEnabled_ = false;

    // Servo trajectory state
    float    servoCurrent_[ESP_MAX_SERVOS];
    float    servoStart_[ESP_MAX_SERVOS];
    float    servoTarget_[ESP_MAX_SERVOS];
    uint32_t servoStartMs_[ESP_MAX_SERVOS];
    uint32_t servoDurationMs_[ESP_MAX_SERVOS];
    bool     servoActive_[ESP_MAX_SERVOS];
};
