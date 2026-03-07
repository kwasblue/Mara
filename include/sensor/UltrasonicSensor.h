// include/sensor/UltrasonicSensor.h
// Self-registering ultrasonic sensor
//
// Uses Pins:: constants from PinConfig.h for hardware configuration.
// Automatically registers with SensorRegistry.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_ULTRASONIC

#include "sensor/ISensor.h"
#include "sensor/SensorMacros.h"
#include "config/PinConfig.h"
#include <Arduino.h>

namespace mara {

class UltrasonicSensor : public ISensor {
public:
    static constexpr const char* NAME = "ultrasonic";
    static constexpr uint8_t MAX_SENSORS = 4;
    static constexpr uint32_t DEFAULT_SAMPLE_INTERVAL_MS = 50;
    static constexpr uint32_t PULSE_TIMEOUT_US = 30000;

    struct Reading {
        int trigPin = -1;
        int echoPin = -1;
        bool attached = false;
        float lastDistance = -1.0f;
        uint32_t lastSampleMs = 0;
    };

    // ISensor interface
    const char* name() const override { return NAME; }

    uint32_t requiredCaps() const override {
        return SensorCap::ULTRASONIC;
    }

    void init() override {
        // Auto-configure from Pins:: constants
        #ifdef Pins_ULTRA0_TRIG
        attach(0, Pins::ULTRA0_TRIG, Pins::ULTRA0_ECHO);
        #endif
        #ifdef Pins_ULTRA1_TRIG
        attach(1, Pins::ULTRA1_TRIG, Pins::ULTRA1_ECHO);
        #endif
        #ifdef Pins_ULTRA2_TRIG
        attach(2, Pins::ULTRA2_TRIG, Pins::ULTRA2_ECHO);
        #endif
        #ifdef Pins_ULTRA3_TRIG
        attach(3, Pins::ULTRA3_TRIG, Pins::ULTRA3_ECHO);
        #endif

        // If no preprocessor pins defined, use namespace constants
        if (!hasAnyAttached()) {
            // Try default pins from namespace
            attach(0, Pins::ULTRA0_TRIG, Pins::ULTRA0_ECHO);
        }

        online_ = hasAnyAttached();
    }

    void loop(uint32_t now_ms) override {
        // Round-robin sampling to spread blocking
        for (uint8_t i = 0; i < MAX_SENSORS; ++i) {
            uint8_t id = (lastSampledId_ + 1 + i) % MAX_SENSORS;
            auto& r = readings_[id];

            if (!r.attached) continue;
            if ((now_ms - r.lastSampleMs) < sampleIntervalMs_) continue;

            sampleSensor(id, now_ms);
            lastSampledId_ = id;
            return;  // Only one per loop call
        }
    }

    void toJson(JsonObject& out) const override {
        for (uint8_t i = 0; i < MAX_SENSORS; ++i) {
            if (readings_[i].attached) {
                char key[8];
                snprintf(key, sizeof(key), "d%u", i);
                out[key] = readings_[i].lastDistance;
            }
        }
    }

    // Public API
    bool attach(uint8_t id, int trigPin, int echoPin) {
        if (id >= MAX_SENSORS) return false;

        pinMode(trigPin, OUTPUT);
        pinMode(echoPin, INPUT);

        readings_[id].trigPin = trigPin;
        readings_[id].echoPin = echoPin;
        readings_[id].attached = true;
        readings_[id].lastDistance = -1.0f;
        readings_[id].lastSampleMs = 0;

        return true;
    }

    bool isAttached(uint8_t id) const {
        return (id < MAX_SENSORS) && readings_[id].attached;
    }

    float readDistanceCm(uint8_t id) const {
        if (id >= MAX_SENSORS || !readings_[id].attached) {
            return -1.0f;
        }
        return readings_[id].lastDistance;
    }

    float sampleNow(uint8_t id) {
        if (id >= MAX_SENSORS || !readings_[id].attached) {
            return -1.0f;
        }
        sampleSensor(id, millis());
        return readings_[id].lastDistance;
    }

    void setSampleInterval(uint32_t ms) { sampleIntervalMs_ = ms; }
    uint32_t getSampleInterval() const { return sampleIntervalMs_; }

private:
    Reading readings_[MAX_SENSORS];
    uint32_t sampleIntervalMs_ = DEFAULT_SAMPLE_INTERVAL_MS;
    uint8_t lastSampledId_ = 0;

    bool hasAnyAttached() const {
        for (uint8_t i = 0; i < MAX_SENSORS; ++i) {
            if (readings_[i].attached) return true;
        }
        return false;
    }

    void sampleSensor(uint8_t id, uint32_t now_ms) {
        auto& r = readings_[id];

        digitalWrite(r.trigPin, LOW);
        delayMicroseconds(2);
        digitalWrite(r.trigPin, HIGH);
        delayMicroseconds(10);
        digitalWrite(r.trigPin, LOW);

        unsigned long duration = pulseIn(r.echoPin, HIGH, PULSE_TIMEOUT_US);
        r.lastSampleMs = now_ms;

        if (duration == 0) {
            r.lastDistance = -1.0f;
            return;
        }

        r.lastDistance = (duration * 0.0343f) / 2.0f;
    }
};

REGISTER_SENSOR(UltrasonicSensor);

} // namespace mara

#else // !HAS_ULTRASONIC

// Stub when disabled - no registration
namespace mara {
class UltrasonicSensor {
public:
    static constexpr const char* NAME = "ultrasonic";
    bool attach(uint8_t, int, int) { return false; }
    bool isAttached(uint8_t) const { return false; }
    float readDistanceCm(uint8_t) const { return -1.0f; }
    float sampleNow(uint8_t) { return -1.0f; }
    void setSampleInterval(uint32_t) {}
    uint32_t getSampleInterval() const { return 0; }
};
}

#endif // HAS_ULTRASONIC
