// include/config/MaraConfig.h
// Unified robot configuration with runtime override support
//
// This consolidates all configuration structs into a single hierarchy.
// Configs can be set at compile time (defaults) or runtime (via commands/JSON).

#pragma once

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>

namespace config {

// =============================================================================
// Safety Configuration
// =============================================================================
struct Safety {
    uint32_t host_timeout_ms = 3000;   // Time without heartbeat → DISCONNECTED
    uint32_t motion_timeout_ms = 500;  // Time without motion cmd → auto-stop
    float max_linear_vel = 2.0f;       // m/s, commands clamped to this
    float max_angular_vel = 3.14f;     // rad/s, commands clamped to this
    int estop_pin = -1;                // Physical E-stop button pin (-1 = none)
    int bypass_pin = -1;               // Safety bypass jumper (-1 = none)
    int relay_pin = -1;                // Power relay for motor enable (-1 = none)
};

// =============================================================================
// Loop Rate Configuration
// =============================================================================
struct LoopRates {
    uint16_t control_hz = 50;   // Main control update (MotionController, etc)
    uint16_t safety_hz = 100;   // Safety checks / E-stop / watchdog
    uint16_t telemetry_hz = 10; // Telemetry send interval

    // Limits
    static constexpr uint16_t CONTROL_HZ_MIN = 5;
    static constexpr uint16_t CONTROL_HZ_MAX = 200;
    static constexpr uint16_t SAFETY_HZ_MIN = 20;
    static constexpr uint16_t SAFETY_HZ_MAX = 500;
    static constexpr uint16_t TELEMETRY_HZ_MIN = 1;
    static constexpr uint16_t TELEMETRY_HZ_MAX = 50;

    // Helpers
    uint32_t control_period_ms() const { return control_hz ? 1000 / control_hz : 1000; }
    uint32_t safety_period_ms() const { return safety_hz ? 1000 / safety_hz : 1000; }
    uint32_t telemetry_period_ms() const { return telemetry_hz ? 1000 / telemetry_hz : 1000; }
};

// =============================================================================
// Control Task Configuration (FreeRTOS)
// =============================================================================
struct ControlTask {
    bool enabled = true;            // Use FreeRTOS task (true) or cooperative (false)
    uint16_t rate_hz = 100;         // Control loop rate
    uint16_t stack_size = 4096;     // Stack size in bytes
    uint8_t priority = 5;           // Task priority (0-24)
    uint8_t core = 1;               // Core to run on (0=WiFi, 1=recommended)
};

// =============================================================================
// Network Configuration
// =============================================================================
struct Network {
    const char* device_name = "ESP32-bot";
    uint32_t serial_baud = 115200;
    uint16_t tcp_port = 3333;

    // WiFi (configured via separate AP/STA config)
    bool wifi_enabled = true;
    bool ble_enabled = false;
    bool mqtt_enabled = false;

    // MQTT settings (if enabled)
    const char* mqtt_broker = nullptr;
    uint16_t mqtt_port = 1883;
};

// =============================================================================
// Motion Configuration
// =============================================================================
struct Motion {
    // Differential drive
    float wheel_base = 0.25f;       // Distance between wheels (m)
    float max_linear = 0.5f;        // Max linear velocity (m/s)
    float max_angular = 2.0f;       // Max angular velocity (rad/s)
    float max_linear_accel = 1.0f;  // Max linear acceleration (m/s^2)
    float max_angular_accel = 2.0f; // Max angular acceleration (rad/s^2)

    // Motor IDs
    uint8_t left_motor_id = 0;
    uint8_t right_motor_id = 1;
};

// =============================================================================
// Unified Robot Configuration
// =============================================================================
struct MaraConfig {
    Safety safety;
    LoopRates rates;
    ControlTask control_task;
    Network network;
    Motion motion;

    // Version for config compatibility checking
    static constexpr uint16_t CONFIG_VERSION = 1;

    /// Apply runtime overrides from JSON
    /// Returns true if any values were changed
    bool applyOverrides(const char* json);

    /// Validate current configuration values.
    /// Returns human-readable issues; empty means configuration is sane.
    std::vector<std::string> validate() const;

    /// Clamp obviously-invalid values back to safe defaults.
    /// Returns true if any value was changed.
    bool sanitize();

    /// Serialize config to JSON for saving/transmission
    /// Returns number of bytes written (excluding null terminator)
    int toJson(char* buffer, size_t bufferSize) const;

    /// Get default configuration
    static MaraConfig defaults() { return MaraConfig{}; }
};

// =============================================================================
// Global Config Access
// =============================================================================

/// Get the active robot configuration (mutable)
MaraConfig& getMaraConfig();

/// Reset config to defaults
void resetMaraConfig();

} // namespace config
