// AUTO-GENERATED from SensorDef("temp")
// Implement init() and loop() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_TEMP_SENSOR

#include "sensor/ISensor.h"
#include <ArduinoJson.h>

namespace mara {

class TemperatureSensor : public ISensor {
public:
    // Auto-generated from telemetry fields
    struct Reading {
        uint8_t sensor_id = 0;
        uint8_t ok = 0;
        int16_t temp_centi = 0;
    };

    const char* name() const override { return "temp"; }
    uint32_t sampleIntervalMs() const override { return 50; }

    void init() override {
        // TODO: Initialize hardware (I2C, GPIO, etc.)
        online_ = true;
    }

    void loop(uint32_t now_ms) override {
        if (!online_) return;

        // TODO: Sample hardware and update reading_
        // Example for i2c interface:
        //   reading_.value = readHardware();

        lastSampleMs_ = now_ms;
    }

    void toJson(JsonObject& out) const override {
        out["sensor_id"] = reading_.sensor_id;
        out["ok"] = reading_.ok;
        out["temp_centi"] = reading_.temp_centi;
    }

    const Reading& reading() const { return reading_; }

private:
    Reading reading_;
    uint32_t lastSampleMs_ = 0;
};

} // namespace mara

#endif // HAS_TEMP_SENSOR
