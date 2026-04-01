#pragma once

#include "config/FeatureFlags.h"
#include "hal/IServo.h"
#include "core/Debug.h"

/// Servo motor manager using HAL abstraction.
/// Supports multiple servos with calibration (offset/scale).
class ServoManager {
public:
    ServoManager() = default;

    /// Set the HAL servo interface (required before use)
    void setHal(hal::IServo* servo) { hal_ = servo; }

    void attach(int servoId, int pin, int minUs = 500, int maxUs = 2500) {
        if (!hal_) {
            DBG_PRINTLN("[ServoManager] attach: HAL not set");
            return;
        }

        if (servoId < 0 || servoId >= static_cast<int>(hal_->maxServos())) {
            DBG_PRINTF("[ServoManager] attach: invalid servoId=%d (max=%d)\n",
                       servoId, hal_->maxServos());
            return;
        }

        DBG_PRINTF("[ServoManager] attach id=%d pin=%d min=%d max=%d\n",
                   servoId, pin, minUs, maxUs);

        bool ok = hal_->attach(static_cast<uint8_t>(servoId),
                               static_cast<uint8_t>(pin),
                               static_cast<uint16_t>(minUs),
                               static_cast<uint16_t>(maxUs));

        if (!ok) {
            DBG_PRINTLN("[ServoManager] attach FAILED");
        }
    }

    void detach(int servoId) {
        if (!hal_) return;
        if (servoId < 0 || servoId >= static_cast<int>(hal_->maxServos())) return;
        if (!hal_->attached(static_cast<uint8_t>(servoId))) return;

        DBG_PRINTF("[ServoManager] detach id=%d\n", servoId);
        hal_->detach(static_cast<uint8_t>(servoId));
    }

    void setAngle(int servoId, float angleDeg) {
        if (!hal_) return;
        if (servoId < 0 || servoId >= static_cast<int>(hal_->maxServos())) return;
        if (!hal_->attached(static_cast<uint8_t>(servoId))) {
            DBG_PRINTLN("[ServoManager] setAngle ignored, not attached");
            return;
        }

        float logical = angleDeg;

        // logicalAngle → internal = offset + scale * angle
        logical = offsetDeg_ + scale_ * logical;

        // Clamp for servo [0, 180]
        if (logical < 0.0f)   logical = 0.0f;
        if (logical > 180.0f) logical = 180.0f;

        DBG_PRINTF("[ServoManager] setAngle id=%d cmd=%.1f internal=%.1f\n",
                   servoId, angleDeg, logical);

        hal_->write(static_cast<uint8_t>(servoId), logical);
    }

    // Optional calibration APIs
    void setOffset(float offsetDeg) { offsetDeg_ = offsetDeg; }
    void setScale(float scale)      { scale_ = scale; }

private:
    hal::IServo* hal_ = nullptr;

    float offsetDeg_ = 0.0f;
    float scale_     = 1.0f;
};
