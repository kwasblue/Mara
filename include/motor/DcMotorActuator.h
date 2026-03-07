// include/motor/DcMotorActuator.h
// Self-registering DC motor actuator
//
// Uses deferred initialization - gets GpioManager/PwmManager from ServiceContext.
// Auto-configures motors from Pins:: constants.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_DC_MOTOR

#include "motor/IActuator.h"
#include "motor/ActuatorRegistry.h"
#include "motor/PID.h"
#include "config/PinConfig.h"
#include "core/ServiceContext.h"
#include "hw/GpioManager.h"
#include "hw/PwmManager.h"
#include <Arduino.h>

namespace mara {

class DcMotorActuator : public IActuator {
public:
    static constexpr const char* NAME = "dc_motor";
    static constexpr uint8_t MAX_MOTORS = 4;
    static constexpr int GPIO_BASE_CH = 3;
    static constexpr int PWM_BASE_CH = 0;

    struct Motor {
        int in1Pin = -1;
        int in2Pin = -1;
        int pwmPin = -1;
        int ledcChannel = -1;
        int gpioChIn1 = -1;
        int gpioChIn2 = -1;
        int pwmCh = -1;
        bool attached = false;
        float lastSpeed = 0.0f;
        float freqHz = 0.0f;
        int resolution = 0;
        bool pidEnabled = false;
        float targetOmegaRadS = 0.0f;
        PID pid;
    };

    // IActuator interface
    const char* name() const override { return NAME; }

    uint32_t requiredCaps() const override {
        return ActuatorCap::DC_MOTOR;
    }

    void init(ServiceContext& ctx) override {
        gpio_ = ctx.gpio;
        pwm_ = ctx.pwm;

        if (gpio_ && pwm_) {
            online_ = true;
            // Initialize PID defaults
            for (uint8_t i = 0; i < MAX_MOTORS; ++i) {
                motors_[i].pid.setOutputLimits(-1.0f, 1.0f);
                motors_[i].pid.reset();
            }
        }
    }

    void setup() override {
        if (!online_) return;

        // Auto-attach motors from Pins:: constants
        attach(0, Pins::MOTOR_LEFT_IN1, Pins::MOTOR_LEFT_IN2,
               Pins::MOTOR_LEFT_PWM, 0, 15000, 12);

        // Add more motors here if pins defined:
        // attach(1, Pins::MOTOR_RIGHT_IN1, ...);
    }

    void stopAll() override {
        for (uint8_t i = 0; i < MAX_MOTORS; ++i) {
            if (motors_[i].attached) {
                stop(i);
            }
        }
    }

    // DC Motor API
    bool attach(uint8_t id, int in1Pin, int in2Pin, int pwmPin,
                int ledcChannel, int freq = 15000, int resolutionBits = 12) {
        if (id >= MAX_MOTORS || !gpio_ || !pwm_) {
            return false;
        }

        const int gpioChIn1 = GPIO_BASE_CH + id * 2;
        const int gpioChIn2 = GPIO_BASE_CH + id * 2 + 1;
        const int pwmCh = PWM_BASE_CH + id;

        gpio_->registerChannel(gpioChIn1, in1Pin, OUTPUT);
        gpio_->registerChannel(gpioChIn2, in2Pin, OUTPUT);
        gpio_->write(gpioChIn1, LOW);
        gpio_->write(gpioChIn2, LOW);

        pwm_->registerChannel(pwmCh, pwmPin, ledcChannel, static_cast<float>(freq));
        pwm_->set(pwmCh, 0.0f);

        Motor& m = motors_[id];
        m.in1Pin = in1Pin;
        m.in2Pin = in2Pin;
        m.pwmPin = pwmPin;
        m.ledcChannel = ledcChannel;
        m.gpioChIn1 = gpioChIn1;
        m.gpioChIn2 = gpioChIn2;
        m.pwmCh = pwmCh;
        m.attached = true;
        m.lastSpeed = 0.0f;
        m.freqHz = static_cast<float>(freq);
        m.resolution = resolutionBits;
        m.pid.setOutputLimits(-1.0f, 1.0f);
        m.pid.reset();
        m.pidEnabled = false;
        m.targetOmegaRadS = 0.0f;

        return true;
    }

    bool isAttached(uint8_t id) const {
        return (id < MAX_MOTORS) && motors_[id].attached;
    }

    bool setSpeed(uint8_t id, float speed) {
        if (id >= MAX_MOTORS || !motors_[id].attached || !gpio_ || !pwm_) {
            return false;
        }

        if (speed > 1.0f) speed = 1.0f;
        if (speed < -1.0f) speed = -1.0f;

        Motor& m = motors_[id];
        m.lastSpeed = speed;
        const float mag = fabsf(speed);

        if (mag == 0.0f) {
            gpio_->write(m.gpioChIn1, LOW);
            gpio_->write(m.gpioChIn2, LOW);
        } else if (speed > 0.0f) {
            gpio_->write(m.gpioChIn1, HIGH);
            gpio_->write(m.gpioChIn2, LOW);
        } else {
            gpio_->write(m.gpioChIn1, LOW);
            gpio_->write(m.gpioChIn2, HIGH);
        }

        pwm_->set(m.pwmCh, mag);
        return true;
    }

    bool stop(uint8_t id) {
        if (id >= MAX_MOTORS || !motors_[id].attached) {
            return false;
        }
        Motor& m = motors_[id];
        if (m.pidEnabled) {
            m.pid.reset();
        }
        m.pidEnabled = false;
        m.targetOmegaRadS = 0.0f;
        return setSpeed(id, 0.0f);
    }

    // PID API
    bool enableVelocityPid(uint8_t id, bool enable) {
        if (id >= MAX_MOTORS || !motors_[id].attached) return false;
        motors_[id].pidEnabled = enable;
        motors_[id].pid.reset();
        return true;
    }

    bool setVelocityTarget(uint8_t id, float omegaRadPerSec) {
        if (id >= MAX_MOTORS || !motors_[id].attached) return false;
        motors_[id].targetOmegaRadS = omegaRadPerSec;
        return true;
    }

    bool setVelocityGains(uint8_t id, float kp, float ki, float kd) {
        if (id >= MAX_MOTORS || !motors_[id].attached) return false;
        motors_[id].pid.setGains(kp, ki, kd);
        return true;
    }

    bool updateVelocityPid(uint8_t id, float measuredOmegaRadS, float dt) {
        if (id >= MAX_MOTORS || !motors_[id].attached) return false;
        Motor& m = motors_[id];
        if (!m.pidEnabled || dt <= 0.0f) return false;
        float cmd = m.pid.compute(m.targetOmegaRadS, measuredOmegaRadS, dt);
        return setSpeed(id, cmd);
    }

    float getLastSpeed(uint8_t id) const {
        if (id >= MAX_MOTORS) return 0.0f;
        return motors_[id].lastSpeed;
    }

private:
    GpioManager* gpio_ = nullptr;
    PwmManager* pwm_ = nullptr;
    Motor motors_[MAX_MOTORS];
};

REGISTER_ACTUATOR(DcMotorActuator);

} // namespace mara

#else // !HAS_DC_MOTOR

namespace mara {
class DcMotorActuator {
public:
    static constexpr const char* NAME = "dc_motor";
    bool attach(uint8_t, int, int, int, int, int = 15000, int = 12) { return false; }
    bool isAttached(uint8_t) const { return false; }
    bool setSpeed(uint8_t, float) { return false; }
    bool stop(uint8_t) { return false; }
    void stopAll() {}
};
}

#endif // HAS_DC_MOTOR
