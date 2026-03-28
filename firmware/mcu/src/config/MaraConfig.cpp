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

std::vector<std::string> MaraConfig::validate() const {
    std::vector<std::string> issues;

    if (safety.host_timeout_ms < 100) {
        issues.emplace_back("safety.host_timeout_ms must be >= 100");
    }
    if (safety.motion_timeout_ms < 10) {
        issues.emplace_back("safety.motion_timeout_ms must be >= 10");
    }
    if (safety.max_linear_vel <= 0.0f) {
        issues.emplace_back("safety.max_linear_vel must be positive");
    }
    if (safety.max_angular_vel <= 0.0f) {
        issues.emplace_back("safety.max_angular_vel must be positive");
    }

    if (rates.control_hz < LoopRates::CONTROL_HZ_MIN || rates.control_hz > LoopRates::CONTROL_HZ_MAX) {
        issues.emplace_back("rates.control_hz out of range");
    }
    if (rates.safety_hz < LoopRates::SAFETY_HZ_MIN || rates.safety_hz > LoopRates::SAFETY_HZ_MAX) {
        issues.emplace_back("rates.safety_hz out of range");
    }
    if (rates.telemetry_hz < LoopRates::TELEMETRY_HZ_MIN || rates.telemetry_hz > LoopRates::TELEMETRY_HZ_MAX) {
        issues.emplace_back("rates.telemetry_hz out of range");
    }

    if (control_task.rate_hz == 0) {
        issues.emplace_back("control_task.rate_hz must be > 0");
    }
    if (network.serial_baud == 0) {
        issues.emplace_back("network.serial_baud must be > 0");
    }
    if (network.tcp_port == 0) {
        issues.emplace_back("network.tcp_port must be > 0");
    }

    if (motion.wheel_base <= 0.0f) {
        issues.emplace_back("motion.wheel_base must be positive");
    }
    if (motion.max_linear <= 0.0f) {
        issues.emplace_back("motion.max_linear must be positive");
    }
    if (motion.max_angular <= 0.0f) {
        issues.emplace_back("motion.max_angular must be positive");
    }

    return issues;
}

bool MaraConfig::sanitize() {
    bool changed = false;

    if (safety.host_timeout_ms < 100) {
        safety.host_timeout_ms = MaraConfig::defaults().safety.host_timeout_ms;
        changed = true;
    }
    if (safety.motion_timeout_ms < 10) {
        safety.motion_timeout_ms = MaraConfig::defaults().safety.motion_timeout_ms;
        changed = true;
    }
    if (safety.max_linear_vel <= 0.0f) {
        safety.max_linear_vel = MaraConfig::defaults().safety.max_linear_vel;
        changed = true;
    }
    if (safety.max_angular_vel <= 0.0f) {
        safety.max_angular_vel = MaraConfig::defaults().safety.max_angular_vel;
        changed = true;
    }

    if (rates.control_hz < LoopRates::CONTROL_HZ_MIN || rates.control_hz > LoopRates::CONTROL_HZ_MAX) {
        rates.control_hz = MaraConfig::defaults().rates.control_hz;
        changed = true;
    }
    if (rates.safety_hz < LoopRates::SAFETY_HZ_MIN || rates.safety_hz > LoopRates::SAFETY_HZ_MAX) {
        rates.safety_hz = MaraConfig::defaults().rates.safety_hz;
        changed = true;
    }
    if (rates.telemetry_hz < LoopRates::TELEMETRY_HZ_MIN || rates.telemetry_hz > LoopRates::TELEMETRY_HZ_MAX) {
        rates.telemetry_hz = MaraConfig::defaults().rates.telemetry_hz;
        changed = true;
    }

    if (control_task.rate_hz == 0) {
        control_task.rate_hz = MaraConfig::defaults().control_task.rate_hz;
        changed = true;
    }
    if (network.serial_baud == 0) {
        network.serial_baud = MaraConfig::defaults().network.serial_baud;
        changed = true;
    }
    if (network.tcp_port == 0) {
        network.tcp_port = MaraConfig::defaults().network.tcp_port;
        changed = true;
    }
    if (motion.wheel_base <= 0.0f) {
        motion.wheel_base = MaraConfig::defaults().motion.wheel_base;
        changed = true;
    }
    if (motion.max_linear <= 0.0f) {
        motion.max_linear = MaraConfig::defaults().motion.max_linear;
        changed = true;
    }
    if (motion.max_angular <= 0.0f) {
        motion.max_angular = MaraConfig::defaults().motion.max_angular;
        changed = true;
    }

    return changed;
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
