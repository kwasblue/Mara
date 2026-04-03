// include/hal/IOta.h
// Abstract OTA (Over-The-Air) update interface.
// Wraps platform-specific OTA mechanisms (ArduinoOTA, ESP-IDF OTA, etc.)
#pragma once

#include <cstdint>

namespace hal {

/// OTA update type
enum class OtaType : uint8_t {
    FIRMWARE = 0,  // Main application firmware
    FILESYSTEM = 1 // SPIFFS/LittleFS partition
};

/// OTA error codes
enum class OtaError : uint8_t {
    NONE = 0,
    AUTH_FAILED = 1,
    BEGIN_FAILED = 2,
    CONNECT_FAILED = 3,
    RECEIVE_FAILED = 4,
    END_FAILED = 5,
    UNKNOWN = 255  // Unrecognized error code from platform
};

/// OTA progress callback signature
/// @param progress Current progress (0-total)
/// @param total Total bytes expected
using OtaProgressCallback = void (*)(uint32_t progress, uint32_t total);

/// OTA start callback signature
/// @param type Type of update (firmware or filesystem)
using OtaStartCallback = void (*)(OtaType type);

/// OTA end callback signature
using OtaEndCallback = void (*)();

/// OTA error callback signature
/// @param error Error that occurred
using OtaErrorCallback = void (*)(OtaError error);

/// Abstract OTA interface.
/// Platform implementations wrap ArduinoOTA, ESP-IDF OTA, etc.
///
/// Usage:
///   IOta* ota = hal.ota;
///   ota->setHostname("my-robot");
///   ota->begin();
///   // In loop:
///   ota->handle();
class IOta {
public:
    virtual ~IOta() = default;

    /// Set device hostname for OTA discovery
    /// @param hostname Device hostname (e.g., "robot1")
    virtual void setHostname(const char* hostname) = 0;

    /// Set OTA password for authentication
    /// @param password OTA password (nullptr for no auth)
    virtual void setPassword(const char* password) = 0;

    /// Set OTA port
    /// @param port OTA port (default: 3232)
    virtual void setPort(uint16_t port) = 0;

    /// Set progress callback
    virtual void onProgress(OtaProgressCallback callback) = 0;

    /// Set start callback
    virtual void onStart(OtaStartCallback callback) = 0;

    /// Set end callback
    virtual void onEnd(OtaEndCallback callback) = 0;

    /// Set error callback
    virtual void onError(OtaErrorCallback callback) = 0;

    /// Initialize OTA system
    /// Must be called after WiFi is connected
    virtual void begin() = 0;

    /// Handle OTA events (call in main loop)
    virtual void handle() = 0;

    /// Check if OTA update is in progress
    virtual bool isUpdating() const = 0;
};

} // namespace hal
