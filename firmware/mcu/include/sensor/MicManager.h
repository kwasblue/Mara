// managers/MicManager.h
#pragma once

#include <Arduino.h>
#include "driver/i2s.h"

class MicManager {
public:
    struct Level {
        float rms = 0.0f;   // 0..1 (normalized)
        float peak = 0.0f;  // 0..1
        float dbfs = -120.0f; // dBFS approx
    };

    MicManager() : port_(I2S_NUM_0), online_(false) {}

    bool begin(gpio_num_t wsPin,
               gpio_num_t sckPin,
               gpio_num_t sdPin,
               i2s_port_t port = I2S_NUM_0);

    bool isOnline() const { return online_; }

    // Collect a small buffer and compute RMS/peak/dbfs
    bool readLevel(Level& outLevel,
                   size_t sampleCount = 512);

private:
    i2s_port_t port_;
    bool       online_;
};
