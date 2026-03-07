#pragma once

#include "config/FeatureFlags.h"

#if HAS_ULTRASONIC

#include <Arduino.h>
#include "core/Debug.h"

class UltrasonicManager {
public:
    static constexpr uint8_t MAX_SENSORS = 4;
    static constexpr uint32_t DEFAULT_SAMPLE_INTERVAL_MS = 50;  // 20Hz max sample rate
    static constexpr uint32_t PULSE_TIMEOUT_US = 30000;         // 30ms max pulse wait

    struct Sensor {
        int trigPin   = -1;
        int echoPin   = -1;
        bool attached = false;
        float lastDistance = -1.0f;     // Cached value
        uint32_t lastSampleMs = 0;      // When last sampled
        bool samplePending = false;     // Sampling in progress
    };

    UltrasonicManager() = default;

    /// Set minimum interval between samples (prevents blocking too often)
    void setSampleInterval(uint32_t ms) { sampleIntervalMs_ = ms; }
    uint32_t getSampleInterval() const { return sampleIntervalMs_; }

    bool attach(uint8_t id, int trigPin, int echoPin) {
        if (id >= MAX_SENSORS) {
            DBG_PRINTF("[Ultrasonic] attach failed, id=%u out of range\n", id);
            return false;
        }

        pinMode(trigPin, OUTPUT);
        pinMode(echoPin, INPUT);

        sensors_[id].trigPin  = trigPin;
        sensors_[id].echoPin  = echoPin;
        sensors_[id].attached = true;
        sensors_[id].lastDistance = -1.0f;
        sensors_[id].lastSampleMs = 0;

        DBG_PRINTF("[Ultrasonic] attach id=%u trig=%d echo=%d\n", id, trigPin, echoPin);
        return true;
    }

    bool isAttached(uint8_t id) const {
        return (id < MAX_SENSORS) && sensors_[id].attached;
    }

    /// Call this periodically (e.g., in a low-priority loop) to update cached values.
    /// Only samples one sensor per call to spread blocking across multiple loop iterations.
    void loop(uint32_t now_ms) {
        // Find next sensor that needs sampling
        for (uint8_t i = 0; i < MAX_SENSORS; ++i) {
            uint8_t id = (lastSampledId_ + 1 + i) % MAX_SENSORS;
            auto& s = sensors_[id];

            if (!s.attached) continue;
            if ((now_ms - s.lastSampleMs) < sampleIntervalMs_) continue;

            // Sample this sensor (blocking, but only one per loop call)
            sampleSensor(id, now_ms);
            lastSampledId_ = id;
            return;  // Only sample one per call
        }
    }

    /// Returns cached distance (cm), or negative on error/no data.
    /// Non-blocking - returns immediately with last known value.
    float readDistanceCm(uint8_t id) const {
        if (id >= MAX_SENSORS || !sensors_[id].attached) {
            return -1.0f;
        }
        return sensors_[id].lastDistance;
    }

    /// Force an immediate sample (blocking). Use sparingly.
    float sampleNow(uint8_t id) {
        if (id >= MAX_SENSORS || !sensors_[id].attached) {
            return -1.0f;
        }
        sampleSensor(id, millis());
        return sensors_[id].lastDistance;
    }

    /// Get the age of the cached reading in ms
    uint32_t getReadingAgeMs(uint8_t id, uint32_t now_ms) const {
        if (id >= MAX_SENSORS || !sensors_[id].attached) {
            return UINT32_MAX;
        }
        return now_ms - sensors_[id].lastSampleMs;
    }

private:
    Sensor sensors_[MAX_SENSORS];
    uint32_t sampleIntervalMs_ = DEFAULT_SAMPLE_INTERVAL_MS;
    uint8_t lastSampledId_ = 0;

    void sampleSensor(uint8_t id, uint32_t now_ms) {
        auto& s = sensors_[id];

        // Trigger pulse
        digitalWrite(s.trigPin, LOW);
        delayMicroseconds(2);
        digitalWrite(s.trigPin, HIGH);
        delayMicroseconds(10);
        digitalWrite(s.trigPin, LOW);

        // Measure echo (blocking, but only ~30ms max)
        unsigned long duration = pulseIn(s.echoPin, HIGH, PULSE_TIMEOUT_US);

        s.lastSampleMs = now_ms;

        if (duration == 0) {
            s.lastDistance = -1.0f;  // Timeout/no echo
            return;
        }

        // Speed of sound ≈ 0.0343 cm/µs; divide by 2 (round trip)
        s.lastDistance = (duration * 0.0343f) / 2.0f;
    }
};

#else // !HAS_ULTRASONIC

// Stub when ultrasonic is disabled
class UltrasonicManager {
public:
    static constexpr uint8_t MAX_SENSORS = 4;

    UltrasonicManager() = default;
    void setSampleInterval(uint32_t) {}
    uint32_t getSampleInterval() const { return 0; }
    bool attach(uint8_t, int, int) { return false; }
    bool isAttached(uint8_t) const { return false; }
    void loop(uint32_t) {}
    float readDistanceCm(uint8_t) const { return -1.0f; }
    float sampleNow(uint8_t) { return -1.0f; }
    uint32_t getReadingAgeMs(uint8_t, uint32_t) const { return UINT32_MAX; }
};

#endif // HAS_ULTRASONIC
