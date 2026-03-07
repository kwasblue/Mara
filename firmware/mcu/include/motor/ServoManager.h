#pragma once

#include "config/FeatureFlags.h"

#if HAS_SERVO

#include <Arduino.h>
#include <ESP32Servo.h>
#include "core/Debug.h"

class ServoManager {
public:
    ServoManager() = default;

    void attach(int servoId, int pin, int minUs = 500, int maxUs = 2500) {
        if (servoId != 0) {
            DBG_PRINTF("[ServoManager] attach: unsupported servoId=%d (only 0 allowed)\n",
                       servoId);
            return;
        }

        pin_   = pin;
        minUs_ = minUs;
        maxUs_ = maxUs;

        DBG_PRINTF("[ServoManager] attach id=%d pin=%d min=%d max=%d\n",
                   servoId, pin, minUs, maxUs);

        // IMPORTANT: no setPeriodHertz() here – it was breaking your program.
        int ch = servo_.attach(pin, minUs, maxUs);
        DBG_PRINTF("[ServoManager] attach returned channel=%d\n", ch);

        attached_ = (ch >= 0);
        if (!attached_) {
            DBG_PRINTLN("[ServoManager] attach FAILED");
        }
    }

    void detach(int servoId) {
        if (servoId != 0) return;
        if (!attached_)  return;

        DBG_PRINTF("[ServoManager] detach id=%d\n", servoId);

        servo_.detach();
        attached_ = false;
        pin_ = -1;
    }

    void setAngle(int servoId, float angleDeg) {
        if (servoId != 0) return;
        if (!attached_) {
            DBG_PRINTLN("[ServoManager] setAngle ignored, not attached");
            return;
        }

        float logical = angleDeg;

        // logicalAngle → internal = offset + scale * angle
        logical = offsetDeg_ + scale_ * logical;

        // Clamp for servo library [0, 180]
        if (logical < 0.0f)   logical = 0.0f;
        if (logical > 180.0f) logical = 180.0f;

        DBG_PRINTF("[ServoManager] setAngle id=%d cmd=%.1f internal=%.1f on pin=%d\n",
                   servoId, angleDeg, logical, pin_);

        servo_.write(logical);
    }

    // Optional calibration APIs
    void setOffset(float offsetDeg) { offsetDeg_ = offsetDeg; }
    void setScale(float scale)      { scale_ = scale; }

private:
    Servo servo_;
    bool  attached_ = false;
    int   pin_      = -1;
    int   minUs_    = 500;
    int   maxUs_    = 2400;

    float offsetDeg_ = 0.0f;
    float scale_     = 1.0f;
};

#else // !HAS_SERVO

// Stub when servo is disabled
class ServoManager {
public:
    ServoManager() = default;
    void attach(int, int, int = 500, int = 2500) {}
    void detach(int) {}
    void setAngle(int, float) {}
    void setOffset(float) {}
    void setScale(float) {}
};

#endif // HAS_SERVO
