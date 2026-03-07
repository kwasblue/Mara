// src/motor/DcMotorManager.cpp
// DC Motor Manager implementation

#include "motor/DcMotorManager.h"

#if HAS_DC_MOTOR

#include "core/Debug.h"

bool DcMotorManager::attach(uint8_t id,
                            int in1Pin,
                            int in2Pin,
                            int pwmPin,
                            int ledcChannel,
                            int freq,
                            int resolutionBits)
{
    if (id >= MAX_MOTORS) {
        DBG_PRINTF("[DcMotorManager] attach failed, id=%u out of range\n", id);
        return false;
    }

    // Use a base that matches the auto-generated channels.
    const int gpioChIn1 = GPIO_BASE_CH + id * 2;
    const int gpioChIn2 = GPIO_BASE_CH + id * 2 + 1;
    const int pwmCh     = PWM_BASE_CH  + id;

    // Configure direction pins via GpioManager
    gpio_.registerChannel(gpioChIn1, in1Pin, OUTPUT);
    gpio_.registerChannel(gpioChIn2, in2Pin, OUTPUT);
    gpio_.write(gpioChIn1, LOW);
    gpio_.write(gpioChIn2, LOW);

    // Configure PWM via PwmManager
    pwm_.registerChannel(pwmCh, pwmPin, ledcChannel, static_cast<float>(freq));
    pwm_.set(pwmCh, 0.0f);

    Motor& m      = motors_[id];
    m.in1Pin      = in1Pin;
    m.in2Pin      = in2Pin;
    m.pwmPin      = pwmPin;
    m.ledcChannel = ledcChannel;
    m.gpioChIn1   = gpioChIn1;
    m.gpioChIn2   = gpioChIn2;
    m.pwmCh       = pwmCh;
    m.attached    = true;
    m.lastSpeed   = 0.0f;
    m.freqHz      = static_cast<float>(freq);
    m.resolution  = resolutionBits;

    // PID defaults for this motor
    m.pid.setOutputLimits(-1.0f, 1.0f);
    m.pid.reset();
    m.pidEnabled      = false;
    m.targetOmegaRadS = 0.0f;

    DBG_PRINTF(
        "[DcMotorManager] attach id=%u in1=%d in2=%d pwmPin=%d ledcCH=%d "
        "gpioChIn1=%d gpioChIn2=%d pwmCh=%d freq=%d res=%d\n",
        id, in1Pin, in2Pin, pwmPin, ledcChannel,
        gpioChIn1, gpioChIn2, pwmCh, freq, resolutionBits
    );
    return true;
}

bool DcMotorManager::setSpeed(uint8_t id, float speed) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        DBG_PRINTF("[DcMotorManager] setSpeed ignored, id=%u not attached\n", id);
        return false;
    }

    if (speed >  1.0f) speed =  1.0f;
    if (speed < -1.0f) speed = -1.0f;

    Motor& m     = motors_[id];
    m.lastSpeed  = speed;
    const float mag = fabsf(speed);  // 0..1

    // Direction via GpioManager
    if (mag == 0.0f) {
        gpio_.write(m.gpioChIn1, LOW);
        gpio_.write(m.gpioChIn2, LOW);
    } else if (speed > 0.0f) {
        gpio_.write(m.gpioChIn1, HIGH);
        gpio_.write(m.gpioChIn2, LOW);
    } else {
        gpio_.write(m.gpioChIn1, LOW);
        gpio_.write(m.gpioChIn2, HIGH);
    }

    // PWM duty via PwmManager
    pwm_.set(m.pwmCh, mag);

    DBG_PRINTF("[DcMotorManager] id=%u speed=%.3f mag=%.3f\n",
               id, speed, mag);
    return true;
}

bool DcMotorManager::stop(uint8_t id) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        return false;
    }
    Motor& m = motors_[id];

    // Reset PID before disabling (order matters!)
    if (m.pidEnabled) {
        m.pid.reset();
    }

    m.pidEnabled = false;
    m.targetOmegaRadS = 0.0f;

    return setSpeed(id, 0.0f);
}

void DcMotorManager::stopAll() {
    for (uint8_t i = 0; i < MAX_MOTORS; ++i) {
        if (motors_[i].attached) {
            stop(i);
        }
    }
}

bool DcMotorManager::getMotorDebugInfo(uint8_t id, MotorDebugInfo& out) const {
    if (id >= MAX_MOTORS) {
        return false;
    }
    const Motor& m = motors_[id];

    out.id          = id;
    out.attached    = m.attached;
    out.in1Pin      = m.in1Pin;
    out.in2Pin      = m.in2Pin;
    out.pwmPin      = m.pwmPin;
    out.ledcChannel = m.ledcChannel;
    out.gpioChIn1   = m.gpioChIn1;
    out.gpioChIn2   = m.gpioChIn2;
    out.pwmCh       = m.pwmCh;
    out.lastSpeed   = m.lastSpeed;
    out.freqHz      = m.freqHz;
    out.resolution  = m.resolution;

    out.pidEnabled      = m.pidEnabled;
    out.targetOmegaRadS = m.targetOmegaRadS;

    return m.attached;
}

void DcMotorManager::dumpAllMotorMappings() const {
    DBG_PRINTF("=== DcMotorManager mappings ===\n");
    for (uint8_t id = 0; id < MAX_MOTORS; ++id) {
        const Motor& m = motors_[id];
        if (!m.attached) {
            DBG_PRINTF("  id=%u: [NOT ATTACHED]\n", id);
            continue;
        }

        DBG_PRINTF(
            "  id=%u: in1Pin=%d in2Pin=%d pwmPin=%d ledcCH=%d "
            "gpioChIn1=%d gpioChIn2=%d pwmCh=%d freq=%.1fHz "
            "res=%d lastSpeed=%.3f pidEnabled=%d targetOmega=%.3f rad/s\n",
            id,
            m.in1Pin,
            m.in2Pin,
            m.pwmPin,
            m.ledcChannel,
            m.gpioChIn1,
            m.gpioChIn2,
            m.pwmCh,
            m.freqHz,
            m.resolution,
            m.lastSpeed,
            m.pidEnabled ? 1 : 0,
            m.targetOmegaRadS
        );
    }
    DBG_PRINTF("=== end DcMotorManager mappings ===\n");
}

bool DcMotorManager::enableVelocityPid(uint8_t id, bool enable) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        DBG_PRINTF("[DcMotorManager] enableVelocityPid ignored, id=%u not attached\n", id);
        return false;
    }
    Motor& m = motors_[id];
    m.pidEnabled = enable;
    m.pid.reset();
    DBG_PRINTF("[DcMotorManager] id=%u PID %s\n", id, enable ? "ENABLED" : "DISABLED");
    return true;
}

bool DcMotorManager::setVelocityTarget(uint8_t id, float omegaRadPerSec) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        DBG_PRINTF("[DcMotorManager] setVelocityTarget ignored, id=%u not attached\n", id);
        return false;
    }
    motors_[id].targetOmegaRadS = omegaRadPerSec;
    DBG_PRINTF("[DcMotorManager] id=%u targetOmega=%.3f rad/s\n", id, omegaRadPerSec);
    return true;
}

bool DcMotorManager::setVelocityGains(uint8_t id, float kp, float ki, float kd) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        DBG_PRINTF("[DcMotorManager] setVelocityGains ignored, id=%u not attached\n", id);
        return false;
    }
    Motor& m = motors_[id];
    m.pid.setGains(kp, ki, kd);
    DBG_PRINTF("[DcMotorManager] id=%u PID gains kp=%.4f ki=%.4f kd=%.4f\n",
               id, kp, ki, kd);
    return true;
}

bool DcMotorManager::updateVelocityPid(uint8_t id, float measuredOmegaRadS, float dt) {
    if (id >= MAX_MOTORS || !motors_[id].attached) {
        return false;
    }
    Motor& m = motors_[id];
    if (!m.pidEnabled) {
        return false;
    }
    if (dt <= 0.0f) {
        return false;
    }

    float cmd = m.pid.compute(m.targetOmegaRadS, measuredOmegaRadS, dt);
    // cmd should be within -1..1 due to PID output limits
    return setSpeed(id, cmd);
}

#endif // HAS_DC_MOTOR
