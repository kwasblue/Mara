#include "camera/MotionDetector.h"
#include "utils/Logger.h"

static const char* TAG = "Motion";

MotionDetector::MotionDetector() {}

void MotionDetector::configure(const MotionConfig& config) {
    enabled_ = config.enabled;
    sensitivity_ = config.sensitivity;
    threshold_ = config.threshold;
    cooldownMs_ = config.cooldownMs;
    LOG_INFO(TAG, "Motion config: enabled=%d, sens=%d, thresh=%d, cooldown=%dms",
             enabled_, sensitivity_, threshold_, cooldownMs_);
}

void MotionDetector::setEnabled(bool enabled) {
    enabled_ = enabled;
    if (!enabled && prevFrame_) {
        free(prevFrame_);
        prevFrame_ = nullptr;
        prevFrameLen_ = 0;
    }
    LOG_INFO(TAG, "Motion detection %s", enabled ? "enabled" : "disabled");
}

void MotionDetector::setCallback(MotionCallback callback) {
    callback_ = callback;
}

bool MotionDetector::processFrame(camera_fb_t* fb) {
    if (!enabled_ || !fb || fb->len == 0) {
        return false;
    }

    uint32_t now = millis();

    // Check cooldown
    if (now - lastMotionTime_ < cooldownMs_) {
        return false;
    }

    // First frame - just store it
    if (!prevFrame_) {
        prevFrame_ = (uint8_t*)malloc(fb->len);
        if (prevFrame_) {
            memcpy(prevFrame_, fb->buf, fb->len);
            prevFrameLen_ = fb->len;
        }
        return false;
    }

    // Frame size changed - reallocate
    if (fb->len != prevFrameLen_) {
        free(prevFrame_);
        prevFrame_ = (uint8_t*)malloc(fb->len);
        if (prevFrame_) {
            memcpy(prevFrame_, fb->buf, fb->len);
            prevFrameLen_ = fb->len;
        }
        return false;
    }

    // Calculate difference
    lastChangePercent_ = calculateDifference(prevFrame_, fb->buf, fb->len);

    // Store current frame for next comparison
    memcpy(prevFrame_, fb->buf, fb->len);

    // Check if motion threshold exceeded
    // Sensitivity inverts: higher sensitivity = lower trigger threshold
    uint8_t triggerThreshold = 100 - sensitivity_;

    bool motionDetected = lastChangePercent_ > triggerThreshold;

    if (motionDetected) {
        lastMotionTime_ = now;
        LOG_INFO(TAG, "Motion detected! Change: %d%%", lastChangePercent_);
        if (callback_) {
            callback_();
        }
    }

    return motionDetected;
}

uint8_t MotionDetector::calculateDifference(const uint8_t* frame1, const uint8_t* frame2, size_t len) {
    // Sample the frames to reduce computation
    // For JPEG, we compare raw bytes which gives a rough approximation
    size_t sampleStep = len / 1000;  // Check ~1000 points
    if (sampleStep < 1) sampleStep = 1;

    size_t changedPixels = 0;
    size_t totalSamples = 0;

    for (size_t i = 0; i < len; i += sampleStep) {
        totalSamples++;
        int diff = abs((int)frame1[i] - (int)frame2[i]);
        if (diff > threshold_) {
            changedPixels++;
        }
    }

    if (totalSamples == 0) return 0;

    return (uint8_t)((changedPixels * 100) / totalSamples);
}
