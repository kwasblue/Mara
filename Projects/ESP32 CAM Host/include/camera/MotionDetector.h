#pragma once

#include <Arduino.h>
#include "esp_camera.h"
#include "storage/ConfigStore.h"

// Motion detection callback
typedef void (*MotionCallback)(void);

class MotionDetector {
public:
    MotionDetector();

    // Configure motion detection
    void configure(const MotionConfig& config);

    // Enable/disable detection
    void setEnabled(bool enabled);
    bool isEnabled() const { return enabled_; }

    // Set callback for motion events
    void setCallback(MotionCallback callback);

    // Process a frame for motion (call periodically)
    // Returns true if motion was detected
    bool processFrame(camera_fb_t* fb);

    // Get last motion detection time
    uint32_t getLastMotionTime() const { return lastMotionTime_; }

    // Get change percentage from last check
    uint8_t getLastChangePercent() const { return lastChangePercent_; }

private:
    bool enabled_ = false;
    uint8_t sensitivity_ = 30;
    uint8_t threshold_ = 15;
    uint32_t cooldownMs_ = 5000;

    uint8_t* prevFrame_ = nullptr;
    size_t prevFrameLen_ = 0;
    uint32_t lastMotionTime_ = 0;
    uint8_t lastChangePercent_ = 0;
    MotionCallback callback_ = nullptr;

    // Compare frames and calculate difference
    uint8_t calculateDifference(const uint8_t* frame1, const uint8_t* frame2, size_t len);
};
