#pragma once

#include "config/FeatureFlags.h"

#if HAS_DC_MOTOR

#include <Arduino.h>
#include <cstdint>
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include "motor/PID.h"

class DcMotorManager {
public:
    static constexpr uint8_t MAX_MOTORS = 4;

    // GPIO channel base for direction pins (matches auto-generated GPIO_CHANNEL_DEFS)
    static constexpr int GPIO_BASE_CH = 3;
    static constexpr int PWM_BASE_CH  = 0;

    struct Motor {
        int in1Pin      = -1;
        int in2Pin      = -1;
        int pwmPin      = -1;

        int ledcChannel = -1;  // hardware LEDC channel (0..15)

        int gpioChIn1   = -1;  // logical channels in GpioManager
        int gpioChIn2   = -1;
        int pwmCh       = -1;  // logical PWM channel in PwmManager

        bool  attached   = false;
        float lastSpeed  = 0.0f;  // -1.0 .. +1.0
        float freqHz     = 0.0f;
        int   resolution = 0;

        // PID / velocity control
        bool  pidEnabled      = false;
        float targetOmegaRadS = 0.0f;
        PID   pid;
    };

    struct MotorDebugInfo {
        uint8_t id       = 0;
        bool    attached = false;

        int in1Pin       = -1;
        int in2Pin       = -1;
        int pwmPin       = -1;
        int ledcChannel  = -1;

        int gpioChIn1    = -1;
        int gpioChIn2    = -1;
        int pwmCh        = -1;

        float lastSpeed  = 0.0f;
        float freqHz     = 0.0f;
        int   resolution = 0;

        bool  pidEnabled      = false;
        float targetOmegaRadS = 0.0f;
    };

    DcMotorManager(GpioManager& gpio, PwmManager& pwm)
        : gpio_(gpio), pwm_(pwm)
    {
        for (uint8_t i = 0; i < MAX_MOTORS; ++i) {
            motors_[i].pid.setOutputLimits(-1.0f, 1.0f);
            motors_[i].pid.reset();
            motors_[i].pidEnabled      = false;
            motors_[i].targetOmegaRadS = 0.0f;
        }
    }

    // Attach a motor to physical pins
    bool attach(uint8_t id,
                int in1Pin,
                int in2Pin,
                int pwmPin,
                int ledcChannel,
                int freq = 15000,
                int resolutionBits = 12);

    // Check if motor is attached
    bool isAttached(uint8_t id) const {
        return (id < MAX_MOTORS) && motors_[id].attached;
    }

    // Set motor speed (-1.0 to +1.0)
    bool setSpeed(uint8_t id, float speed);

    // Stop motor and reset PID
    bool stop(uint8_t id);

    // Stop all attached motors
    void stopAll();

    // Get debug info for a motor
    bool getMotorDebugInfo(uint8_t id, MotorDebugInfo& out) const;

    // Dump all motor mappings to debug output
    void dumpAllMotorMappings() const;

    // === PID / velocity control API ===

    // Enable/disable closed-loop velocity control
    bool enableVelocityPid(uint8_t id, bool enable);

    // Check if velocity PID is enabled
    bool isVelocityPidEnabled(uint8_t id) const {
        return (id < MAX_MOTORS) && motors_[id].attached && motors_[id].pidEnabled;
    }

    // Set target velocity in rad/s
    bool setVelocityTarget(uint8_t id, float omegaRadPerSec);

    // Set PID gains
    bool setVelocityGains(uint8_t id, float kp, float ki, float kd);

    // Update PID with measured velocity (call at fixed rate)
    bool updateVelocityPid(uint8_t id, float measuredOmegaRadS, float dt);

private:
    GpioManager& gpio_;
    PwmManager&  pwm_;

    Motor motors_[MAX_MOTORS];
};

#else // !HAS_DC_MOTOR

class GpioManager;
class PwmManager;

// Stub when DC motor is disabled
class DcMotorManager {
public:
    static constexpr uint8_t MAX_MOTORS = 4;
    struct Motor {};
    struct MotorDebugInfo {
        uint8_t id = 0;
        bool attached = false;
        int in1Pin = -1;
        int in2Pin = -1;
        int pwmPin = -1;
        int ledcChannel = -1;
        int gpioChIn1 = -1;
        int gpioChIn2 = -1;
        int pwmCh = -1;
        float lastSpeed = 0.0f;
        float freqHz = 0.0f;
        int resolution = 0;
        bool pidEnabled = false;
        float targetOmegaRadS = 0.0f;
    };

    DcMotorManager(GpioManager&, PwmManager&) {}
    bool attach(uint8_t, int, int, int, int, int = 15000, int = 12) { return false; }
    bool isAttached(uint8_t) const { return false; }
    bool setSpeed(uint8_t, float) { return false; }
    bool stop(uint8_t) { return false; }
    void stopAll() {}
    bool getMotorDebugInfo(uint8_t, MotorDebugInfo&) const { return false; }
    void dumpAllMotorMappings() const {}
    bool enableVelocityPid(uint8_t, bool) { return false; }
    bool isVelocityPidEnabled(uint8_t) const { return false; }
    bool setVelocityTarget(uint8_t, float) { return false; }
    bool setVelocityGains(uint8_t, float, float, float) { return false; }
    bool updateVelocityPid(uint8_t, float, float) { return false; }
};

#endif // HAS_DC_MOTOR
