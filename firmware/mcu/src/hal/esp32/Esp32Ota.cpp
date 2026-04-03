// src/hal/esp32/Esp32Ota.cpp
// ESP32 OTA implementation using ArduinoOTA

#include "config/PlatformConfig.h"

#if PLATFORM_ESP32

#include "hal/esp32/Esp32Ota.h"
#include <ArduinoOTA.h>

namespace hal {

// Static callback storage
OtaProgressCallback Esp32Ota::progressCallback_ = nullptr;
OtaStartCallback Esp32Ota::startCallback_ = nullptr;
OtaEndCallback Esp32Ota::endCallback_ = nullptr;
OtaErrorCallback Esp32Ota::errorCallback_ = nullptr;
bool Esp32Ota::isUpdating_ = false;
bool Esp32Ota::initialized_ = false;

Esp32Ota::Esp32Ota() {
    // Default configuration will be set via setters
}

void Esp32Ota::setHostname(const char* hostname) {
    ArduinoOTA.setHostname(hostname);
}

void Esp32Ota::setPassword(const char* password) {
    if (password) {
        ArduinoOTA.setPassword(password);
    }
}

void Esp32Ota::setPort(uint16_t port) {
    ArduinoOTA.setPort(port);
}

void Esp32Ota::onProgress(OtaProgressCallback callback) {
    progressCallback_ = callback;
}

void Esp32Ota::onStart(OtaStartCallback callback) {
    startCallback_ = callback;
}

void Esp32Ota::onEnd(OtaEndCallback callback) {
    endCallback_ = callback;
}

void Esp32Ota::onError(OtaErrorCallback callback) {
    errorCallback_ = callback;
}

void Esp32Ota::begin() {
    // Guard against duplicate initialization (ArduinoOTA accumulates callbacks)
    if (initialized_) {
        return;
    }
    initialized_ = true;

    // Wire up callbacks to ArduinoOTA
    ArduinoOTA.onStart([]() {
        isUpdating_ = true;
        if (startCallback_) {
            OtaType type = (ArduinoOTA.getCommand() == U_FLASH)
                ? OtaType::FIRMWARE
                : OtaType::FILESYSTEM;
            startCallback_(type);
        }
    });

    ArduinoOTA.onEnd([]() {
        isUpdating_ = false;
        if (endCallback_) {
            endCallback_();
        }
    });

    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        if (progressCallback_) {
            progressCallback_(progress, total);
        }
    });

    ArduinoOTA.onError([](ota_error_t error) {
        isUpdating_ = false;
        if (errorCallback_) {
            OtaError otaErr;
            switch (error) {
                case OTA_AUTH_ERROR:    otaErr = OtaError::AUTH_FAILED; break;
                case OTA_BEGIN_ERROR:   otaErr = OtaError::BEGIN_FAILED; break;
                case OTA_CONNECT_ERROR: otaErr = OtaError::CONNECT_FAILED; break;
                case OTA_RECEIVE_ERROR: otaErr = OtaError::RECEIVE_FAILED; break;
                case OTA_END_ERROR:     otaErr = OtaError::END_FAILED; break;
                default:                otaErr = OtaError::UNKNOWN; break;
            }
            errorCallback_(otaErr);
        }
    });

    ArduinoOTA.begin();
}

void Esp32Ota::handle() {
    ArduinoOTA.handle();
}

bool Esp32Ota::isUpdating() const {
    return isUpdating_;
}

} // namespace hal

#endif // PLATFORM_ESP32
