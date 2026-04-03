// include/hal/esp32/Esp32Ota.h
// ESP32 OTA implementation using ArduinoOTA
#pragma once

#include "../IOta.h"

namespace hal {

/// ESP32 OTA implementation wrapping ArduinoOTA.
/// Provides OTA firmware updates over WiFi.
class Esp32Ota : public IOta {
public:
    Esp32Ota();

    void setHostname(const char* hostname) override;
    void setPassword(const char* password) override;
    void setPort(uint16_t port) override;

    void onProgress(OtaProgressCallback callback) override;
    void onStart(OtaStartCallback callback) override;
    void onEnd(OtaEndCallback callback) override;
    void onError(OtaErrorCallback callback) override;

    void begin() override;
    void handle() override;
    bool isUpdating() const override;

private:
    // Callbacks stored for delegation
    static OtaProgressCallback progressCallback_;
    static OtaStartCallback startCallback_;
    static OtaEndCallback endCallback_;
    static OtaErrorCallback errorCallback_;
    static bool isUpdating_;
    static bool initialized_;  // Guard against duplicate begin() calls
};

} // namespace hal
