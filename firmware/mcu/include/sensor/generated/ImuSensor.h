// AUTO-GENERATED from SensorDef("imu")
// Implement init() and loop() with hardware-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_IMU

#include "sensor/ISensor.h"
#include <ArduinoJson.h>

namespace mara {

class ImuSensor : public ISensor {
public:
    // Auto-generated from telemetry fields
    struct Reading {
        uint8_t online = 0;
        uint8_t ok = 0;
        int16_t ax_mg = 0;
        int16_t ay_mg = 0;
        int16_t az_mg = 0;
        int16_t gx_mdps = 0;
        int16_t gy_mdps = 0;
        int16_t gz_mdps = 0;
        int16_t temp_c_centi = 0;
    };

    const char* name() const override { return "imu"; }
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
        out["online"] = reading_.online;
        out["ok"] = reading_.ok;
        out["ax_mg"] = reading_.ax_mg;
        out["ay_mg"] = reading_.ay_mg;
        out["az_mg"] = reading_.az_mg;
        out["gx_mdps"] = reading_.gx_mdps;
        out["gy_mdps"] = reading_.gy_mdps;
        out["gz_mdps"] = reading_.gz_mdps;
        out["temp_c_centi"] = reading_.temp_c_centi;
    }

    const Reading& reading() const { return reading_; }

private:
    Reading reading_;
    uint32_t lastSampleMs_ = 0;
};

} // namespace mara

#endif // HAS_IMU
