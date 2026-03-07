// src/config/MaraConfig.cpp
// Unified robot configuration implementation

#include "config/MaraConfig.h"
#include <ArduinoJson.h>
#include <cstring>

namespace config {

// Global config instance
static MaraConfig g_robotConfig;

MaraConfig& getMaraConfig() {
    return g_robotConfig;
}

void resetMaraConfig() {
    g_robotConfig = MaraConfig::defaults();
}

bool MaraConfig::applyOverrides(const char* json) {
    if (!json || !*json) return false;

    JsonDocument doc;
    if (deserializeJson(doc, json) != DeserializationError::Ok) {
        return false;
    }

    bool changed = false;

    // Safety overrides
    if (doc["safety"].is<JsonObject>()) {
        JsonVariantConst s = doc["safety"];
        if (s["host_timeout_ms"].is<uint32_t>()) {
            safety.host_timeout_ms = s["host_timeout_ms"];
            changed = true;
        }
        if (s["motion_timeout_ms"].is<uint32_t>()) {
            safety.motion_timeout_ms = s["motion_timeout_ms"];
            changed = true;
        }
        if (s["max_linear_vel"].is<float>()) {
            safety.max_linear_vel = s["max_linear_vel"];
            changed = true;
        }
        if (s["max_angular_vel"].is<float>()) {
            safety.max_angular_vel = s["max_angular_vel"];
            changed = true;
        }
    }

    // Rates overrides
    if (doc["rates"].is<JsonObject>()) {
        JsonVariantConst r = doc["rates"];
        if (r["control_hz"].is<uint16_t>()) {
            uint16_t hz = r["control_hz"];
            if (hz >= LoopRates::CONTROL_HZ_MIN && hz <= LoopRates::CONTROL_HZ_MAX) {
                rates.control_hz = hz;
                changed = true;
            }
        }
        if (r["safety_hz"].is<uint16_t>()) {
            uint16_t hz = r["safety_hz"];
            if (hz >= LoopRates::SAFETY_HZ_MIN && hz <= LoopRates::SAFETY_HZ_MAX) {
                rates.safety_hz = hz;
                changed = true;
            }
        }
        if (r["telemetry_hz"].is<uint16_t>()) {
            uint16_t hz = r["telemetry_hz"];
            if (hz >= LoopRates::TELEMETRY_HZ_MIN && hz <= LoopRates::TELEMETRY_HZ_MAX) {
                rates.telemetry_hz = hz;
                changed = true;
            }
        }
    }

    // Control task overrides
    if (doc["control_task"].is<JsonObject>()) {
        JsonVariantConst ct = doc["control_task"];
        if (ct["enabled"].is<bool>()) {
            control_task.enabled = ct["enabled"];
            changed = true;
        }
        if (ct["rate_hz"].is<uint16_t>()) {
            control_task.rate_hz = ct["rate_hz"];
            changed = true;
        }
    }

    // Motion overrides
    if (doc["motion"].is<JsonObject>()) {
        JsonVariantConst m = doc["motion"];
        if (m["wheel_base"].is<float>()) {
            motion.wheel_base = m["wheel_base"];
            changed = true;
        }
        if (m["max_linear"].is<float>()) {
            motion.max_linear = m["max_linear"];
            changed = true;
        }
        if (m["max_angular"].is<float>()) {
            motion.max_angular = m["max_angular"];
            changed = true;
        }
    }

    return changed;
}

int MaraConfig::toJson(char* buffer, size_t bufferSize) const {
    JsonDocument doc;

    // Safety
    JsonObject s = doc["safety"].to<JsonObject>();
    s["host_timeout_ms"] = safety.host_timeout_ms;
    s["motion_timeout_ms"] = safety.motion_timeout_ms;
    s["max_linear_vel"] = safety.max_linear_vel;
    s["max_angular_vel"] = safety.max_angular_vel;

    // Rates
    JsonObject r = doc["rates"].to<JsonObject>();
    r["control_hz"] = rates.control_hz;
    r["safety_hz"] = rates.safety_hz;
    r["telemetry_hz"] = rates.telemetry_hz;

    // Control task
    JsonObject ct = doc["control_task"].to<JsonObject>();
    ct["enabled"] = control_task.enabled;
    ct["rate_hz"] = control_task.rate_hz;
    ct["priority"] = control_task.priority;
    ct["core"] = control_task.core;

    // Network
    JsonObject n = doc["network"].to<JsonObject>();
    n["device_name"] = network.device_name;
    n["tcp_port"] = network.tcp_port;

    // Motion
    JsonObject m = doc["motion"].to<JsonObject>();
    m["wheel_base"] = motion.wheel_base;
    m["max_linear"] = motion.max_linear;
    m["max_angular"] = motion.max_angular;

    // Version
    doc["version"] = CONFIG_VERSION;

    return serializeJson(doc, buffer, bufferSize);
}

} // namespace config
