// AUTO-GENERATED from SensorDef("ultrasonic")
// Implement init() and loop() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_ULTRASONIC

#include "sensor/ISensor.h"
#include <ArduinoJson.h>

namespace mara {

class UltrasonicSensor : public ISensor {
public:
    // Auto-generated from telemetry fields
    struct Reading {
        uint8_t sensor_id = 0;
        uint8_t attached = 0;
        uint8_t ok = 0;
        uint16_t dist_mm = 0;
    };

    const char* name() const override { return "ultrasonic"; }
    uint32_t sampleIntervalMs() const override { return 50; }

    void init() override {
        // TODO: Initialize hardware (I2C, GPIO, etc.)
        online_ = true;
    }

    void loop(uint32_t now_ms) override {
        if (!online_) return;

        // TODO: Sample hardware and update reading_
        // Example for gpio interface:
        //   reading_.value = readHardware();

        lastSampleMs_ = now_ms;
    }

    void toJson(JsonObject& out) const override {
        out["sensor_id"] = reading_.sensor_id;
        out["attached"] = reading_.attached;
        out["ok"] = reading_.ok;
        out["dist_mm"] = reading_.dist_mm;
    }

    const Reading& reading() const { return reading_; }

private:
    Reading reading_;
    uint32_t lastSampleMs_ = 0;
};

} // namespace mara

#endif // HAS_ULTRASONIC
