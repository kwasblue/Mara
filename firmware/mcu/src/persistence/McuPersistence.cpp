#include "persistence/McuPersistence.h"

#include <string.h>

#if defined(ARDUINO_ARCH_ESP32)
#include <esp_system.h>
#include <rom/rtc.h>
#endif

namespace persistence {

void McuPersistence::begin(const config::MaraConfig& cfg, uint32_t now_ms) {
    loadDiagnostics_();
    loadConfigMirror_();

    // NOTE: boot_recorded_ is an in-memory flag. If McuPersistence is destroyed
    // and re-created (e.g., in tests), this will re-increment boot_count even
    // though NVS already has the incremented value. For production use where
    // the object persists across reboots, this is correct behavior.
    if (!boot_recorded_) {
        diagnostics_.boot_count += 1;
        diagnostics_.last_boot_ms = now_ms;
        diagnostics_.last_reset_reason = readResetReason_();
        diagnostics_.dirty = true;
        saveDiagnostics_();  // Boot count is always saved immediately
        lastSaveMs_ = now_ms;
        boot_recorded_ = true;
    }

    mirrorConfig(cfg);
    ready_ = true;
}

void McuPersistence::mirrorConfig(const config::MaraConfig& cfg) {
    config_mirror_.version = PersistedConfigMirror{}.version;
    config_mirror_.valid = true;
    config_mirror_.safety = cfg.safety;
    config_mirror_.network = cfg.network;
    const char* name = cfg.network.device_name ? cfg.network.device_name : "";
    strlcpy(config_mirror_.device_name, name, sizeof(config_mirror_.device_name));
    config_mirror_.network.device_name = config_mirror_.device_name;
    saveConfigMirror_();
}

void McuPersistence::updateFromMode(const ModeManager& mode, uint32_t now_ms) {
    const auto& wd = mode.watchdogStats();

    bool changed = false;
    if (diagnostics_.host_timeout_count != wd.host_timeout_count) {
        diagnostics_.host_timeout_count = wd.host_timeout_count;
        diagnostics_.last_host_timeout_ms = wd.last_host_timeout_ms;
        changed = true;
    }
    if (diagnostics_.motion_timeout_count != wd.motion_timeout_count) {
        diagnostics_.motion_timeout_count = wd.motion_timeout_count;
        diagnostics_.last_motion_timeout_ms = wd.last_motion_timeout_ms;
        changed = true;
    }
    if (diagnostics_.host_recovery_count != wd.host_recovery_count) {
        diagnostics_.host_recovery_count = wd.host_recovery_count;
        changed = true;
    }
    if (diagnostics_.last_fault != wd.last_fault) {
        diagnostics_.last_fault = wd.last_fault;
        diagnostics_.last_fault_ms = now_ms;
        if (wd.last_fault == FaultCode::ESTOP) {
            diagnostics_.estop_count += 1;
            diagnostics_.last_estop_ms = now_ms;
        }
        changed = true;
    }

    if (changed) {
        diagnostics_.dirty = true;
        // Debounce NVS writes to prevent flash wear - save at most once per minute
        // Critical changes (e-stop, faults) are still tracked in memory immediately
        saveIfDirtyAndDebounced_(now_ms);
    }
}

void McuPersistence::saveIfDirtyAndDebounced_(uint32_t now_ms) {
    if (!diagnostics_.dirty) {
        return;
    }
    // Only write to NVS if enough time has passed since last write
    if (now_ms - lastSaveMs_ >= kMinSaveIntervalMs) {
        saveDiagnostics_();
        lastSaveMs_ = now_ms;
    }
    // Note: dirty flag remains set if debounced - will be saved on next interval
}

void McuPersistence::resetDiagnostics(uint32_t now_ms) {
    const uint32_t preserved_boot_count = diagnostics_.boot_count;
    const uint32_t preserved_last_boot_ms = diagnostics_.last_boot_ms;
    const uint8_t preserved_last_reset_reason = diagnostics_.last_reset_reason;

    diagnostics_ = PersistedDiagnostics{};
    diagnostics_.boot_count = preserved_boot_count;
    diagnostics_.last_boot_ms = preserved_last_boot_ms;
    diagnostics_.last_reset_reason = preserved_last_reset_reason;
    diagnostics_.dirty = true;
    (void)now_ms;
    saveDiagnostics_();
}

void McuPersistence::fillDiagnostics(JsonObject node) const {
    node["boot_count"] = diagnostics_.boot_count;
    node["last_boot_ms"] = diagnostics_.last_boot_ms;
    node["last_reset_reason"] = diagnostics_.last_reset_reason;
    node["last_fault"] = diagnostics_.last_fault;
    node["last_fault_ms"] = diagnostics_.last_fault_ms;
    node["host_timeout_count"] = diagnostics_.host_timeout_count;
    node["last_host_timeout_ms"] = diagnostics_.last_host_timeout_ms;
    node["motion_timeout_count"] = diagnostics_.motion_timeout_count;
    node["last_motion_timeout_ms"] = diagnostics_.last_motion_timeout_ms;
    node["host_recovery_count"] = diagnostics_.host_recovery_count;
    node["estop_count"] = diagnostics_.estop_count;
    node["last_estop_ms"] = diagnostics_.last_estop_ms;
}

void McuPersistence::fillConfigMirror(JsonObject node) const {
    node["valid"] = config_mirror_.valid;
    node["version"] = config_mirror_.version;
    if (config_mirror_.valid) {
        JsonObject safety = node["safety"].to<JsonObject>();
        safety["host_timeout_ms"] = config_mirror_.safety.host_timeout_ms;
        safety["motion_timeout_ms"] = config_mirror_.safety.motion_timeout_ms;
        safety["max_linear_vel"] = config_mirror_.safety.max_linear_vel;
        safety["max_angular_vel"] = config_mirror_.safety.max_angular_vel;
        safety["estop_pin"] = config_mirror_.safety.estop_pin;
        safety["bypass_pin"] = config_mirror_.safety.bypass_pin;
        safety["relay_pin"] = config_mirror_.safety.relay_pin;

        JsonObject network = node["network"].to<JsonObject>();
        network["device_name"] = config_mirror_.device_name;
        network["serial_baud"] = config_mirror_.network.serial_baud;
        network["tcp_port"] = config_mirror_.network.tcp_port;
        network["wifi_enabled"] = config_mirror_.network.wifi_enabled;
        network["ble_enabled"] = config_mirror_.network.ble_enabled;
        network["mqtt_enabled"] = config_mirror_.network.mqtt_enabled;
        network["mqtt_port"] = config_mirror_.network.mqtt_port;
    }
}

void McuPersistence::fillSnapshot(JsonObject node) const {
    node["ready"] = ready_;
    fillDiagnostics(node["diagnostics"].to<JsonObject>());
    fillConfigMirror(node["config_mirror"].to<JsonObject>());
}

void McuPersistence::fillTelemetry(JsonObject node) const {
    fillSnapshot(node);
}

uint8_t McuPersistence::readResetReason_() const {
    // Use HAL if available
    if (halSystemInfo_) {
        return halSystemInfo_->getResetReasonRaw(0);
    }

#if defined(ARDUINO_ARCH_ESP32)
    return static_cast<uint8_t>(rtc_get_reset_reason(0));
#else
    return 0;
#endif
}

void McuPersistence::loadDiagnostics_() {
    // Use HAL if available
    if (halPersistence_) {
        if (!halPersistence_->begin(kDiagNs, true)) {
            return;
        }
        diagnostics_.boot_count = halPersistence_->getUInt("boot_cnt", 0);
        diagnostics_.last_boot_ms = halPersistence_->getUInt("boot_ms", 0);
        diagnostics_.last_host_timeout_ms = halPersistence_->getUInt("host_to_ms", 0);
        diagnostics_.last_motion_timeout_ms = halPersistence_->getUInt("motion_to", 0);
        diagnostics_.estop_count = halPersistence_->getUInt("estop_cnt", 0);
        diagnostics_.last_estop_ms = halPersistence_->getUInt("estop_ms", 0);
        diagnostics_.last_fault_ms = halPersistence_->getUInt("fault_ms", 0);
        diagnostics_.host_timeout_count = halPersistence_->getUInt("host_to_ct", 0);
        diagnostics_.motion_timeout_count = halPersistence_->getUInt("motion_ct", 0);
        diagnostics_.host_recovery_count = halPersistence_->getUInt("host_recov", 0);
        diagnostics_.last_fault = halPersistence_->getUChar("last_fault", 0);
        diagnostics_.last_reset_reason = halPersistence_->getUChar("reset_rs", 0);
        diagnostics_.firmware_locked = halPersistence_->getBool("fw_locked", false);
        diagnostics_.dirty = false;
        halPersistence_->end();
        return;
    }

#if defined(ARDUINO_ARCH_ESP32)
    Preferences prefs;
    if (!prefs.begin(kDiagNs, true)) {
        return;
    }
    diagnostics_.boot_count = prefs.getUInt("boot_cnt", 0);
    diagnostics_.last_boot_ms = prefs.getUInt("boot_ms", 0);
    diagnostics_.last_host_timeout_ms = prefs.getUInt("host_to_ms", 0);
    diagnostics_.last_motion_timeout_ms = prefs.getUInt("motion_to", 0);
    diagnostics_.estop_count = prefs.getUInt("estop_cnt", 0);
    diagnostics_.last_estop_ms = prefs.getUInt("estop_ms", 0);
    diagnostics_.last_fault_ms = prefs.getUInt("fault_ms", 0);
    diagnostics_.host_timeout_count = prefs.getUInt("host_to_ct", 0);
    diagnostics_.motion_timeout_count = prefs.getUInt("motion_ct", 0);
    diagnostics_.host_recovery_count = prefs.getUInt("host_recov", 0);
    diagnostics_.last_fault = prefs.getUChar("last_fault", 0);
    diagnostics_.last_reset_reason = prefs.getUChar("reset_rs", 0);
    diagnostics_.firmware_locked = prefs.getBool("fw_locked", false);
    diagnostics_.dirty = false;
    prefs.end();
#endif
}

void McuPersistence::saveDiagnostics_() {
    if (!diagnostics_.dirty) {
        return;
    }

    // Use HAL if available
    if (halPersistence_) {
        if (!halPersistence_->begin(kDiagNs, false)) {
            return;
        }
        halPersistence_->putUInt("boot_cnt", diagnostics_.boot_count);
        halPersistence_->putUInt("boot_ms", diagnostics_.last_boot_ms);
        halPersistence_->putUInt("host_to_ms", diagnostics_.last_host_timeout_ms);
        halPersistence_->putUInt("motion_to", diagnostics_.last_motion_timeout_ms);
        halPersistence_->putUInt("estop_cnt", diagnostics_.estop_count);
        halPersistence_->putUInt("estop_ms", diagnostics_.last_estop_ms);
        halPersistence_->putUInt("fault_ms", diagnostics_.last_fault_ms);
        halPersistence_->putUInt("host_to_ct", diagnostics_.host_timeout_count);
        halPersistence_->putUInt("motion_ct", diagnostics_.motion_timeout_count);
        halPersistence_->putUInt("host_recov", diagnostics_.host_recovery_count);
        halPersistence_->putUChar("last_fault", diagnostics_.last_fault);
        halPersistence_->putUChar("reset_rs", diagnostics_.last_reset_reason);
        halPersistence_->end();
        diagnostics_.dirty = false;
        return;
    }

#if defined(ARDUINO_ARCH_ESP32)
    Preferences prefs;
    if (!prefs.begin(kDiagNs, false)) {
        return;
    }
    prefs.putUInt("boot_cnt", diagnostics_.boot_count);
    prefs.putUInt("boot_ms", diagnostics_.last_boot_ms);
    prefs.putUInt("host_to_ms", diagnostics_.last_host_timeout_ms);
    prefs.putUInt("motion_to", diagnostics_.last_motion_timeout_ms);
    prefs.putUInt("estop_cnt", diagnostics_.estop_count);
    prefs.putUInt("estop_ms", diagnostics_.last_estop_ms);
    prefs.putUInt("fault_ms", diagnostics_.last_fault_ms);
    prefs.putUInt("host_to_ct", diagnostics_.host_timeout_count);
    prefs.putUInt("motion_ct", diagnostics_.motion_timeout_count);
    prefs.putUInt("host_recov", diagnostics_.host_recovery_count);
    prefs.putUChar("last_fault", diagnostics_.last_fault);
    prefs.putUChar("reset_rs", diagnostics_.last_reset_reason);
    prefs.end();
    diagnostics_.dirty = false;
#endif
}

void McuPersistence::loadConfigMirror_() {
    // Use HAL if available
    if (halPersistence_) {
        if (!halPersistence_->begin(kCfgNs, true)) {
            return;
        }
        config_mirror_.valid = halPersistence_->getBool("valid", false);
        config_mirror_.version = halPersistence_->getUInt("version", 1);
        config_mirror_.safety.host_timeout_ms = halPersistence_->getUInt("s_host_to", config_mirror_.safety.host_timeout_ms);
        config_mirror_.safety.motion_timeout_ms = halPersistence_->getUInt("s_motion", config_mirror_.safety.motion_timeout_ms);
        config_mirror_.safety.max_linear_vel = halPersistence_->getFloat("s_max_lin", config_mirror_.safety.max_linear_vel);
        config_mirror_.safety.max_angular_vel = halPersistence_->getFloat("s_max_ang", config_mirror_.safety.max_angular_vel);
        config_mirror_.safety.estop_pin = halPersistence_->getInt("s_estop", config_mirror_.safety.estop_pin);
        config_mirror_.safety.bypass_pin = halPersistence_->getInt("s_bypass", config_mirror_.safety.bypass_pin);
        config_mirror_.safety.relay_pin = halPersistence_->getInt("s_relay", config_mirror_.safety.relay_pin);
        halPersistence_->getString("n_name", config_mirror_.device_name, sizeof(config_mirror_.device_name));
        config_mirror_.network.device_name = config_mirror_.device_name;
        config_mirror_.network.serial_baud = halPersistence_->getUInt("n_baud", config_mirror_.network.serial_baud);
        config_mirror_.network.tcp_port = static_cast<uint16_t>(halPersistence_->getUInt("n_tcp", config_mirror_.network.tcp_port));
        config_mirror_.network.wifi_enabled = halPersistence_->getBool("n_wifi", config_mirror_.network.wifi_enabled);
        config_mirror_.network.ble_enabled = halPersistence_->getBool("n_ble", config_mirror_.network.ble_enabled);
        config_mirror_.network.mqtt_enabled = halPersistence_->getBool("n_mqtt", config_mirror_.network.mqtt_enabled);
        config_mirror_.network.mqtt_port = static_cast<uint16_t>(halPersistence_->getUInt("n_mqttp", config_mirror_.network.mqtt_port));
        halPersistence_->end();
        return;
    }

#if defined(ARDUINO_ARCH_ESP32)
    Preferences prefs;
    if (!prefs.begin(kCfgNs, true)) {
        return;
    }
    config_mirror_.valid = prefs.getBool("valid", false);
    config_mirror_.version = prefs.getUInt("version", 1);
    config_mirror_.safety.host_timeout_ms = prefs.getUInt("s_host_to", config_mirror_.safety.host_timeout_ms);
    config_mirror_.safety.motion_timeout_ms = prefs.getUInt("s_motion", config_mirror_.safety.motion_timeout_ms);
    config_mirror_.safety.max_linear_vel = prefs.getFloat("s_max_lin", config_mirror_.safety.max_linear_vel);
    config_mirror_.safety.max_angular_vel = prefs.getFloat("s_max_ang", config_mirror_.safety.max_angular_vel);
    config_mirror_.safety.estop_pin = prefs.getInt("s_estop", config_mirror_.safety.estop_pin);
    config_mirror_.safety.bypass_pin = prefs.getInt("s_bypass", config_mirror_.safety.bypass_pin);
    config_mirror_.safety.relay_pin = prefs.getInt("s_relay", config_mirror_.safety.relay_pin);
    prefs.getString("n_name", config_mirror_.device_name, sizeof(config_mirror_.device_name));
    config_mirror_.network.device_name = config_mirror_.device_name;
    config_mirror_.network.serial_baud = prefs.getUInt("n_baud", config_mirror_.network.serial_baud);
    config_mirror_.network.tcp_port = static_cast<uint16_t>(prefs.getUInt("n_tcp", config_mirror_.network.tcp_port));
    config_mirror_.network.wifi_enabled = prefs.getBool("n_wifi", config_mirror_.network.wifi_enabled);
    config_mirror_.network.ble_enabled = prefs.getBool("n_ble", config_mirror_.network.ble_enabled);
    config_mirror_.network.mqtt_enabled = prefs.getBool("n_mqtt", config_mirror_.network.mqtt_enabled);
    config_mirror_.network.mqtt_port = static_cast<uint16_t>(prefs.getUInt("n_mqttp", config_mirror_.network.mqtt_port));
    prefs.end();
#endif
}

void McuPersistence::saveConfigMirror_() {
    // Use HAL if available
    if (halPersistence_) {
        if (!halPersistence_->begin(kCfgNs, false)) {
            return;
        }
        halPersistence_->putBool("valid", config_mirror_.valid);
        halPersistence_->putUInt("version", config_mirror_.version);
        halPersistence_->putUInt("s_host_to", config_mirror_.safety.host_timeout_ms);
        halPersistence_->putUInt("s_motion", config_mirror_.safety.motion_timeout_ms);
        halPersistence_->putFloat("s_max_lin", config_mirror_.safety.max_linear_vel);
        halPersistence_->putFloat("s_max_ang", config_mirror_.safety.max_angular_vel);
        halPersistence_->putInt("s_estop", config_mirror_.safety.estop_pin);
        halPersistence_->putInt("s_bypass", config_mirror_.safety.bypass_pin);
        halPersistence_->putInt("s_relay", config_mirror_.safety.relay_pin);
        halPersistence_->putString("n_name", config_mirror_.device_name);
        halPersistence_->putUInt("n_baud", config_mirror_.network.serial_baud);
        halPersistence_->putUInt("n_tcp", config_mirror_.network.tcp_port);
        halPersistence_->putBool("n_wifi", config_mirror_.network.wifi_enabled);
        halPersistence_->putBool("n_ble", config_mirror_.network.ble_enabled);
        halPersistence_->putBool("n_mqtt", config_mirror_.network.mqtt_enabled);
        halPersistence_->putUInt("n_mqttp", config_mirror_.network.mqtt_port);
        halPersistence_->end();
        return;
    }

#if defined(ARDUINO_ARCH_ESP32)
    Preferences prefs;
    if (!prefs.begin(kCfgNs, false)) {
        return;
    }
    prefs.putBool("valid", config_mirror_.valid);
    prefs.putUInt("version", config_mirror_.version);
    prefs.putUInt("s_host_to", config_mirror_.safety.host_timeout_ms);
    prefs.putUInt("s_motion", config_mirror_.safety.motion_timeout_ms);
    prefs.putFloat("s_max_lin", config_mirror_.safety.max_linear_vel);
    prefs.putFloat("s_max_ang", config_mirror_.safety.max_angular_vel);
    prefs.putInt("s_estop", config_mirror_.safety.estop_pin);
    prefs.putInt("s_bypass", config_mirror_.safety.bypass_pin);
    prefs.putInt("s_relay", config_mirror_.safety.relay_pin);
    prefs.putString("n_name", config_mirror_.device_name);
    prefs.putUInt("n_baud", config_mirror_.network.serial_baud);
    prefs.putUInt("n_tcp", config_mirror_.network.tcp_port);
    prefs.putBool("n_wifi", config_mirror_.network.wifi_enabled);
    prefs.putBool("n_ble", config_mirror_.network.ble_enabled);
    prefs.putBool("n_mqtt", config_mirror_.network.mqtt_enabled);
    prefs.putUInt("n_mqttp", config_mirror_.network.mqtt_port);
    prefs.end();
#endif
}

void McuPersistence::setFirmwareLocked(bool locked) {
    if (diagnostics_.firmware_locked == locked) {
        return;
    }
    diagnostics_.firmware_locked = locked;
    diagnostics_.dirty = true;

    // Firmware lock state changes are saved immediately
    // Use HAL if available
    if (halPersistence_) {
        if (halPersistence_->begin(kDiagNs, false)) {
            halPersistence_->putBool("fw_locked", locked);
            halPersistence_->end();
        }
        diagnostics_.dirty = false;
        return;
    }

#if defined(ARDUINO_ARCH_ESP32)
    Preferences prefs;
    if (prefs.begin(kDiagNs, false)) {
        prefs.putBool("fw_locked", locked);
        prefs.end();
    }
    diagnostics_.dirty = false;
#endif
}

void McuPersistence::checkPhysicalReset(uint8_t gpioPin, uint32_t holdTimeMs) {
#if defined(ARDUINO_ARCH_ESP32)
    // Check if button is held on boot
    pinMode(gpioPin, INPUT_PULLUP);

    // Wait for pin to stabilize
    delay(100);

    if (digitalRead(gpioPin) == LOW) {
        // Button is pressed - wait for hold time
        uint32_t startMs = millis();
        while (digitalRead(gpioPin) == LOW) {
            if ((millis() - startMs) >= holdTimeMs) {
                // Button held long enough - clear firmware lock
                setFirmwareLocked(false);
                return;
            }
            delay(10);
        }
    }
#else
    (void)gpioPin;
    (void)holdTimeMs;
#endif
}

} // namespace persistence
