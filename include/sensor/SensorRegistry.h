// include/sensor/SensorRegistry.h
// Singleton registry for self-registered sensors
//
// Sensors register via REGISTER_SENSOR() macro in static constructors.
// Registry provides unified init, loop, and telemetry access.

#pragma once

#include <cstdint>
#include <cstddef>
#include <ArduinoJson.h>

namespace mara {

class ISensor;

/// Singleton registry for all sensors
class SensorRegistry {
public:
    static constexpr size_t MAX_SENSORS = 16;

    static SensorRegistry& instance();

    /// Register a sensor (called by REGISTER_SENSOR macro)
    void registerSensor(ISensor* sensor);

    /// Set available capabilities from feature flags
    void setAvailableCaps(uint32_t caps) { availableCaps_ = caps; }
    uint32_t availableCaps() const { return availableCaps_; }

    /// Initialize all registered sensors (call once in setup)
    void initAll();

    /// Update all sensors (call in main loop)
    void loopAll(uint32_t now_ms);

    /// Export all sensor readings to JSON
    /// @param out JSON object - each sensor adds a nested object
    void toJsonAll(JsonObject& out) const;

    /// Find sensor by name
    /// @return Pointer to sensor or nullptr if not found
    ISensor* find(const char* name);
    const ISensor* find(const char* name) const;

    /// Typed sensor lookup
    template<typename T>
    T* get() {
        return static_cast<T*>(find(T::NAME));
    }

    template<typename T>
    const T* get() const {
        return static_cast<const T*>(find(T::NAME));
    }

    /// Number of registered sensors
    size_t count() const { return count_; }

    /// Check if a sensor with given caps is available
    bool hasCaps(uint32_t caps) const {
        return (availableCaps_ & caps) == caps;
    }

    /// Iteration support
    ISensor** begin() { return sensors_; }
    ISensor** end() { return sensors_ + count_; }
    ISensor* const* begin() const { return sensors_; }
    ISensor* const* end() const { return sensors_ + count_; }

private:
    SensorRegistry() = default;

    ISensor* sensors_[MAX_SENSORS] = {};
    size_t count_ = 0;
    uint32_t availableCaps_ = 0;
    bool initialized_ = false;
};

} // namespace mara
