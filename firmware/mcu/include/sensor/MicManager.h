// managers/MicManager.h
#pragma once

#include <Arduino.h>
#include "driver/i2s.h"
#include "hal/II2sAudio.h"

class MicManager {
public:
    struct Level {
        float rms = 0.0f;   // 0..1 (normalized)
        float peak = 0.0f;  // 0..1
        float dbfs = -120.0f; // dBFS approx
    };

    MicManager() : port_(I2S_NUM_0), online_(false), halAudio_(nullptr) {}

    /// Set HAL I2S audio interface (optional, for portable code)
    void setHal(hal::II2sAudio* audio) { halAudio_ = audio; }

    /// Begin with direct ESP32 I2S driver (legacy)
    bool begin(gpio_num_t wsPin,
               gpio_num_t sckPin,
               gpio_num_t sdPin,
               i2s_port_t port = I2S_NUM_0);

    /// Begin with HAL I2S interface (portable)
    bool beginHal(int8_t wsPin, int8_t sckPin, int8_t sdPin);

    bool isOnline() const { return online_; }

    // Collect a small buffer and compute RMS/peak/dbfs
    bool readLevel(Level& outLevel,
                   size_t sampleCount = 512);

    /// End/stop the microphone (release resources)
    void end();

private:
    static constexpr size_t kMaxSampleCount = 1024;

    i2s_port_t port_;
    bool       online_;
    hal::II2sAudio* halAudio_;
    bool       usingHal_ = false;
    // Per-instance buffer to avoid static shared state across concurrent calls.
    // Previously this was a static local variable which would cause data races
    // if readLevel() were called from multiple tasks simultaneously.
    int32_t    sampleBuffer_[kMaxSampleCount];
};
