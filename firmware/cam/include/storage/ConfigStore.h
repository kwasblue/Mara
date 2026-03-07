#pragma once

#include <Arduino.h>
#include <Preferences.h>
#include "esp_camera.h"
#include "config/DefaultSettings.h"

// Camera configuration structure
struct CameraConfig {
    framesize_t frameSize = DEFAULT_FRAME_SIZE;
    uint8_t jpegQuality = DEFAULT_JPEG_QUALITY;
    int8_t brightness = DEFAULT_BRIGHTNESS;
    int8_t contrast = DEFAULT_CONTRAST;
    int8_t saturation = DEFAULT_SATURATION;
    int8_t sharpness = DEFAULT_SHARPNESS;
    uint8_t denoise = DEFAULT_DENOISE;
    uint8_t specialEffect = DEFAULT_SPECIAL_EFFECT;
    bool whiteBalance = DEFAULT_WHITEBAL;
    bool awbGain = DEFAULT_AWB_GAIN;
    uint8_t wbMode = DEFAULT_WB_MODE;
    bool exposureCtrl = DEFAULT_EXPOSURE_CTRL;
    bool aec2 = DEFAULT_AEC2;
    int8_t aeLevel = DEFAULT_AE_LEVEL;
    uint16_t aecValue = DEFAULT_AEC_VALUE;
    bool gainCtrl = DEFAULT_GAIN_CTRL;
    uint8_t agcGain = DEFAULT_AGC_GAIN;
    uint8_t gainCeiling = DEFAULT_GAINCEILING;
    bool bpc = DEFAULT_BPC;
    bool wpc = DEFAULT_WPC;
    bool rawGma = DEFAULT_RAW_GMA;
    bool lenc = DEFAULT_LENC;
    bool hMirror = DEFAULT_HMIRROR;
    bool vFlip = DEFAULT_VFLIP;
    bool dcw = DEFAULT_DCW;
    bool colorbar = DEFAULT_COLORBAR;
};

// Network configuration structure
struct NetworkConfig {
    char ssid[33] = "";
    char password[65] = "";
    char hostname[33] = DEFAULT_HOSTNAME;
    char apSsid[33] = DEFAULT_AP_SSID;
    char apPassword[65] = DEFAULT_AP_PASSWORD;
    uint8_t apChannel = DEFAULT_AP_CHANNEL;
    uint16_t httpPort = DEFAULT_HTTP_PORT;
    bool configured = false;
};

// Motion detection configuration
struct MotionConfig {
    bool enabled = DEFAULT_MOTION_ENABLED;
    uint8_t sensitivity = DEFAULT_MOTION_SENSITIVITY;
    uint8_t threshold = DEFAULT_MOTION_THRESHOLD;
    uint32_t cooldownMs = DEFAULT_MOTION_COOLDOWN_MS;
};

// Security configuration
struct SecurityConfig {
    bool authEnabled = DEFAULT_AUTH_ENABLED;
    uint8_t rateLimit = DEFAULT_RATE_LIMIT;
};

class ConfigStore {
public:
    ConfigStore();

    bool begin();

    // Camera config
    bool loadCameraConfig(CameraConfig& config);
    bool saveCameraConfig(const CameraConfig& config);

    // Network config
    bool loadNetworkConfig(NetworkConfig& config);
    bool saveNetworkConfig(const NetworkConfig& config);

    // Motion config
    bool loadMotionConfig(MotionConfig& config);
    bool saveMotionConfig(const MotionConfig& config);

    // Security config
    bool loadSecurityConfig(SecurityConfig& config);
    bool saveSecurityConfig(const SecurityConfig& config);

    // Factory reset
    bool factoryReset();

private:
    Preferences prefs_;
    static constexpr const char* NAMESPACE_CAMERA = "camera";
    static constexpr const char* NAMESPACE_NETWORK = "network";
    static constexpr const char* NAMESPACE_MOTION = "motion";
    static constexpr const char* NAMESPACE_SECURITY = "security";
};
