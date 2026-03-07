#include "storage/ConfigStore.h"
#include "utils/Logger.h"

static const char* TAG = "ConfigStore";

ConfigStore::ConfigStore() {}

bool ConfigStore::begin() {
    LOG_INFO(TAG, "Initializing NVS config store");
    return true;
}

bool ConfigStore::loadCameraConfig(CameraConfig& config) {
    if (!prefs_.begin(NAMESPACE_CAMERA, true)) {
        LOG_WARN(TAG, "Failed to open camera namespace, using defaults");
        return false;
    }

    config.frameSize = (framesize_t)prefs_.getUChar("frameSize", DEFAULT_FRAME_SIZE);
    config.jpegQuality = prefs_.getUChar("jpegQuality", DEFAULT_JPEG_QUALITY);
    config.brightness = prefs_.getChar("brightness", DEFAULT_BRIGHTNESS);
    config.contrast = prefs_.getChar("contrast", DEFAULT_CONTRAST);
    config.saturation = prefs_.getChar("saturation", DEFAULT_SATURATION);
    config.sharpness = prefs_.getChar("sharpness", DEFAULT_SHARPNESS);
    config.denoise = prefs_.getUChar("denoise", DEFAULT_DENOISE);
    config.specialEffect = prefs_.getUChar("specialFx", DEFAULT_SPECIAL_EFFECT);
    config.whiteBalance = prefs_.getBool("whiteBalance", DEFAULT_WHITEBAL);
    config.awbGain = prefs_.getBool("awbGain", DEFAULT_AWB_GAIN);
    config.wbMode = prefs_.getUChar("wbMode", DEFAULT_WB_MODE);
    config.exposureCtrl = prefs_.getBool("exposureCtrl", DEFAULT_EXPOSURE_CTRL);
    config.aec2 = prefs_.getBool("aec2", DEFAULT_AEC2);
    config.aeLevel = prefs_.getChar("aeLevel", DEFAULT_AE_LEVEL);
    config.aecValue = prefs_.getUShort("aecValue", DEFAULT_AEC_VALUE);
    config.gainCtrl = prefs_.getBool("gainCtrl", DEFAULT_GAIN_CTRL);
    config.agcGain = prefs_.getUChar("agcGain", DEFAULT_AGC_GAIN);
    config.gainCeiling = prefs_.getUChar("gainCeiling", DEFAULT_GAINCEILING);
    config.bpc = prefs_.getBool("bpc", DEFAULT_BPC);
    config.wpc = prefs_.getBool("wpc", DEFAULT_WPC);
    config.rawGma = prefs_.getBool("rawGma", DEFAULT_RAW_GMA);
    config.lenc = prefs_.getBool("lenc", DEFAULT_LENC);
    config.hMirror = prefs_.getBool("hMirror", DEFAULT_HMIRROR);
    config.vFlip = prefs_.getBool("vFlip", DEFAULT_VFLIP);
    config.dcw = prefs_.getBool("dcw", DEFAULT_DCW);
    config.colorbar = prefs_.getBool("colorbar", DEFAULT_COLORBAR);

    prefs_.end();
    LOG_INFO(TAG, "Camera config loaded");
    return true;
}

bool ConfigStore::saveCameraConfig(const CameraConfig& config) {
    if (!prefs_.begin(NAMESPACE_CAMERA, false)) {
        LOG_ERROR(TAG, "Failed to open camera namespace for writing");
        return false;
    }

    prefs_.putUChar("frameSize", (uint8_t)config.frameSize);
    prefs_.putUChar("jpegQuality", config.jpegQuality);
    prefs_.putChar("brightness", config.brightness);
    prefs_.putChar("contrast", config.contrast);
    prefs_.putChar("saturation", config.saturation);
    prefs_.putChar("sharpness", config.sharpness);
    prefs_.putUChar("denoise", config.denoise);
    prefs_.putUChar("specialFx", config.specialEffect);
    prefs_.putBool("whiteBalance", config.whiteBalance);
    prefs_.putBool("awbGain", config.awbGain);
    prefs_.putUChar("wbMode", config.wbMode);
    prefs_.putBool("exposureCtrl", config.exposureCtrl);
    prefs_.putBool("aec2", config.aec2);
    prefs_.putChar("aeLevel", config.aeLevel);
    prefs_.putUShort("aecValue", config.aecValue);
    prefs_.putBool("gainCtrl", config.gainCtrl);
    prefs_.putUChar("agcGain", config.agcGain);
    prefs_.putUChar("gainCeiling", config.gainCeiling);
    prefs_.putBool("bpc", config.bpc);
    prefs_.putBool("wpc", config.wpc);
    prefs_.putBool("rawGma", config.rawGma);
    prefs_.putBool("lenc", config.lenc);
    prefs_.putBool("hMirror", config.hMirror);
    prefs_.putBool("vFlip", config.vFlip);
    prefs_.putBool("dcw", config.dcw);
    prefs_.putBool("colorbar", config.colorbar);

    prefs_.end();
    LOG_INFO(TAG, "Camera config saved");
    return true;
}

bool ConfigStore::loadNetworkConfig(NetworkConfig& config) {
    if (!prefs_.begin(NAMESPACE_NETWORK, true)) {
        LOG_WARN(TAG, "Failed to open network namespace, using defaults");
        return false;
    }

    prefs_.getString("ssid", config.ssid, sizeof(config.ssid));
    prefs_.getString("password", config.password, sizeof(config.password));
    prefs_.getString("hostname", config.hostname, sizeof(config.hostname));
    prefs_.getString("apSsid", config.apSsid, sizeof(config.apSsid));
    prefs_.getString("apPassword", config.apPassword, sizeof(config.apPassword));
    config.apChannel = prefs_.getUChar("apChannel", DEFAULT_AP_CHANNEL);
    config.httpPort = prefs_.getUShort("httpPort", DEFAULT_HTTP_PORT);
    config.configured = prefs_.getBool("configured", false);

    // Apply defaults if empty
    if (strlen(config.hostname) == 0) {
        strncpy(config.hostname, DEFAULT_HOSTNAME, sizeof(config.hostname) - 1);
    }
    if (strlen(config.apSsid) == 0) {
        strncpy(config.apSsid, DEFAULT_AP_SSID, sizeof(config.apSsid) - 1);
    }
    if (strlen(config.apPassword) == 0) {
        strncpy(config.apPassword, DEFAULT_AP_PASSWORD, sizeof(config.apPassword) - 1);
    }

    prefs_.end();
    LOG_INFO(TAG, "Network config loaded (configured=%d)", config.configured);
    return true;
}

bool ConfigStore::saveNetworkConfig(const NetworkConfig& config) {
    if (!prefs_.begin(NAMESPACE_NETWORK, false)) {
        LOG_ERROR(TAG, "Failed to open network namespace for writing");
        return false;
    }

    prefs_.putString("ssid", config.ssid);
    prefs_.putString("password", config.password);
    prefs_.putString("hostname", config.hostname);
    prefs_.putString("apSsid", config.apSsid);
    prefs_.putString("apPassword", config.apPassword);
    prefs_.putUChar("apChannel", config.apChannel);
    prefs_.putUShort("httpPort", config.httpPort);
    prefs_.putBool("configured", config.configured);

    prefs_.end();
    LOG_INFO(TAG, "Network config saved");
    return true;
}

bool ConfigStore::loadMotionConfig(MotionConfig& config) {
    if (!prefs_.begin(NAMESPACE_MOTION, true)) {
        LOG_WARN(TAG, "Failed to open motion namespace, using defaults");
        return false;
    }

    config.enabled = prefs_.getBool("enabled", DEFAULT_MOTION_ENABLED);
    config.sensitivity = prefs_.getUChar("sensitivity", DEFAULT_MOTION_SENSITIVITY);
    config.threshold = prefs_.getUChar("threshold", DEFAULT_MOTION_THRESHOLD);
    config.cooldownMs = prefs_.getUInt("cooldownMs", DEFAULT_MOTION_COOLDOWN_MS);

    prefs_.end();
    LOG_INFO(TAG, "Motion config loaded");
    return true;
}

bool ConfigStore::saveMotionConfig(const MotionConfig& config) {
    if (!prefs_.begin(NAMESPACE_MOTION, false)) {
        LOG_ERROR(TAG, "Failed to open motion namespace for writing");
        return false;
    }

    prefs_.putBool("enabled", config.enabled);
    prefs_.putUChar("sensitivity", config.sensitivity);
    prefs_.putUChar("threshold", config.threshold);
    prefs_.putUInt("cooldownMs", config.cooldownMs);

    prefs_.end();
    LOG_INFO(TAG, "Motion config saved");
    return true;
}

bool ConfigStore::loadSecurityConfig(SecurityConfig& config) {
    if (!prefs_.begin(NAMESPACE_SECURITY, true)) {
        LOG_WARN(TAG, "Failed to open security namespace, using defaults");
        return false;
    }

    config.authEnabled = prefs_.getBool("authEnabled", DEFAULT_AUTH_ENABLED);
    config.rateLimit = prefs_.getUChar("rateLimit", DEFAULT_RATE_LIMIT);

    prefs_.end();
    LOG_INFO(TAG, "Security config loaded");
    return true;
}

bool ConfigStore::saveSecurityConfig(const SecurityConfig& config) {
    if (!prefs_.begin(NAMESPACE_SECURITY, false)) {
        LOG_ERROR(TAG, "Failed to open security namespace for writing");
        return false;
    }

    prefs_.putBool("authEnabled", config.authEnabled);
    prefs_.putUChar("rateLimit", config.rateLimit);

    prefs_.end();
    LOG_INFO(TAG, "Security config saved");
    return true;
}

bool ConfigStore::factoryReset() {
    LOG_WARN(TAG, "Performing factory reset!");

    bool success = true;

    if (prefs_.begin(NAMESPACE_CAMERA, false)) {
        prefs_.clear();
        prefs_.end();
    } else {
        success = false;
    }

    if (prefs_.begin(NAMESPACE_NETWORK, false)) {
        prefs_.clear();
        prefs_.end();
    } else {
        success = false;
    }

    if (prefs_.begin(NAMESPACE_MOTION, false)) {
        prefs_.clear();
        prefs_.end();
    } else {
        success = false;
    }

    if (prefs_.begin(NAMESPACE_SECURITY, false)) {
        prefs_.clear();
        prefs_.end();
    } else {
        success = false;
    }

    LOG_INFO(TAG, "Factory reset %s", success ? "complete" : "had errors");
    return success;
}
