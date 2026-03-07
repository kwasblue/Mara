// include/sensor/ISensor.h
// Base interface for self-registering sensors
//
// Sensors implement this interface and use REGISTER_SENSOR() to auto-register.
// Pins are accessed via Pins:: namespace (from generated PinConfig.h).

#pragma once

#include <cstdint>
#include <ArduinoJson.h>

namespace mara {

/// Base interface for all sensors
class ISensor {
public:
    virtual ~ISensor() = default;

    /// Unique sensor name (e.g., "ultrasonic", "imu", "encoder")
    virtual const char* name() const = 0;

    /// Initialize hardware using Pins:: constants
    /// Called once during SensorRegistry::initAll()
    virtual void init() = 0;

    /// Periodic update (called from main loop or sensor task)
    /// @param now_ms Current time in milliseconds
    virtual void loop(uint32_t now_ms) = 0;

    /// Export current readings to JSON for telemetry
    /// @param out JSON object to populate
    virtual void toJson(JsonObject& out) const = 0;

    /// Required capability flags (for feature gating)
    /// Return 0 if no special capabilities required
    virtual uint32_t requiredCaps() const { return 0; }

    /// Priority for loop ordering (lower = earlier). Default 100.
    virtual int priority() const { return 100; }

    /// Whether sensor initialized successfully
    virtual bool isOnline() const { return online_; }

protected:
    bool online_ = false;
};

/// Capability flags for sensors (mirrors feature flags)
namespace SensorCap {
    constexpr uint32_t NONE       = 0;
    constexpr uint32_t ENCODER    = (1 << 0);
    constexpr uint32_t IMU        = (1 << 1);
    constexpr uint32_t ULTRASONIC = (1 << 2);
    constexpr uint32_t LIDAR      = (1 << 3);
    constexpr uint32_t TEMP       = (1 << 4);
    constexpr uint32_t BATTERY    = (1 << 5);
}

} // namespace mara
