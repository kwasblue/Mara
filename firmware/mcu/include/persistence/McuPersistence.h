#pragma once

#include <stdint.h>

#include <Arduino.h>
#include <ArduinoJson.h>

#if defined(ARDUINO_ARCH_ESP32)
#include <Preferences.h>
#endif

#include "command/ModeManager.h"
#include "config/MaraConfig.h"

namespace persistence {

struct PersistedDiagnostics {
    uint32_t boot_count = 0;
    uint32_t last_boot_ms = 0;
    uint32_t last_host_timeout_ms = 0;
    uint32_t last_motion_timeout_ms = 0;
    uint32_t estop_count = 0;
    uint32_t last_estop_ms = 0;
    uint32_t last_fault_ms = 0;
    uint32_t host_timeout_count = 0;
    uint32_t motion_timeout_count = 0;
    uint32_t host_recovery_count = 0;
    uint8_t last_fault = 0;
    uint8_t last_reset_reason = 0;
    bool dirty = false;
};

struct PersistedConfigMirror {
    uint32_t version = 1;
    bool valid = false;
    char device_name[32] = {0};
    config::Safety safety{};
    config::Network network{};
};

class McuPersistence {
public:
    void begin(const config::MaraConfig& cfg, uint32_t now_ms);
    void mirrorConfig(const config::MaraConfig& cfg);
    void updateFromMode(const ModeManager& mode, uint32_t now_ms);
    void resetDiagnostics(uint32_t now_ms);

    const PersistedDiagnostics& diagnostics() const { return diagnostics_; }
    const PersistedConfigMirror& configMirror() const { return config_mirror_; }
    bool ready() const { return ready_; }

    void fillDiagnostics(JsonObject node) const;
    void fillConfigMirror(JsonObject node) const;
    void fillSnapshot(JsonObject node) const;
    void fillTelemetry(JsonObject node) const;

private:
    static constexpr const char* kDiagNs = "mara_diag";
    static constexpr const char* kCfgNs = "mara_cfg";

    uint8_t readResetReason_() const;
    void loadDiagnostics_();
    void saveDiagnostics_();
    void loadConfigMirror_();
    void saveConfigMirror_();

    PersistedDiagnostics diagnostics_{};
    PersistedConfigMirror config_mirror_{};
    bool ready_ = false;
    bool boot_recorded_ = false;
};

} // namespace persistence
