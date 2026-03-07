// src/sensor/SensorRegistry.cpp
// SensorRegistry implementation

#include "sensor/SensorRegistry.h"
#include "sensor/ISensor.h"
#include <ArduinoJson.h>
#include <cstring>
#include <algorithm>

namespace mara {

SensorRegistry& SensorRegistry::instance() {
    static SensorRegistry s_instance;
    return s_instance;
}

void SensorRegistry::registerSensor(ISensor* sensor) {
    if (!sensor || count_ >= MAX_SENSORS) {
        return;
    }

    // Check for duplicate
    for (size_t i = 0; i < count_; ++i) {
        if (sensors_[i] == sensor) {
            return;
        }
    }

    sensors_[count_++] = sensor;
}

void SensorRegistry::initAll() {
    if (initialized_) {
        return;
    }

    // Sort by priority (lower = earlier)
    std::sort(sensors_, sensors_ + count_,
        [](ISensor* a, ISensor* b) {
            return a->priority() < b->priority();
        });

    // Initialize each sensor that has required capabilities
    for (size_t i = 0; i < count_; ++i) {
        ISensor* sensor = sensors_[i];
        uint32_t required = sensor->requiredCaps();

        // Skip if required capabilities not available
        if ((required & availableCaps_) != required) {
            continue;
        }

        sensor->init();
    }

    initialized_ = true;
}

void SensorRegistry::loopAll(uint32_t now_ms) {
    for (size_t i = 0; i < count_; ++i) {
        ISensor* sensor = sensors_[i];
        uint32_t required = sensor->requiredCaps();

        // Skip disabled sensors
        if ((required & availableCaps_) != required) {
            continue;
        }

        if (sensor->isOnline()) {
            sensor->loop(now_ms);
        }
    }
}

void SensorRegistry::toJsonAll(JsonObject& out) const {
    for (size_t i = 0; i < count_; ++i) {
        const ISensor* sensor = sensors_[i];
        uint32_t required = sensor->requiredCaps();

        // Skip disabled sensors
        if ((required & availableCaps_) != required) {
            continue;
        }

        if (sensor->isOnline()) {
            JsonObject sensorObj = out[sensor->name()].to<JsonObject>();
            sensor->toJson(sensorObj);
        }
    }
}

ISensor* SensorRegistry::find(const char* name) {
    if (!name) return nullptr;

    for (size_t i = 0; i < count_; ++i) {
        if (strcmp(sensors_[i]->name(), name) == 0) {
            return sensors_[i];
        }
    }
    return nullptr;
}

const ISensor* SensorRegistry::find(const char* name) const {
    if (!name) return nullptr;

    for (size_t i = 0; i < count_; ++i) {
        if (strcmp(sensors_[i]->name(), name) == 0) {
            return sensors_[i];
        }
    }
    return nullptr;
}

} // namespace mara
