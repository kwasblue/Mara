#include "camera/CameraManager.h"
#include "utils/Logger.h"

static const char* TAG = "Camera";

CameraManager::CameraManager() {}

bool CameraManager::begin() {
    LOG_INFO(TAG, "Initializing camera...");

    // Configure flash LED
    pinMode(LED_FLASH_PIN, OUTPUT);
    digitalWrite(LED_FLASH_PIN, LOW);
    flashOn_ = false;

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = CAM_PIN_D0;
    config.pin_d1 = CAM_PIN_D1;
    config.pin_d2 = CAM_PIN_D2;
    config.pin_d3 = CAM_PIN_D3;
    config.pin_d4 = CAM_PIN_D4;
    config.pin_d5 = CAM_PIN_D5;
    config.pin_d6 = CAM_PIN_D6;
    config.pin_d7 = CAM_PIN_D7;
    config.pin_xclk = CAM_PIN_XCLK;
    config.pin_pclk = CAM_PIN_PCLK;
    config.pin_vsync = CAM_PIN_VSYNC;
    config.pin_href = CAM_PIN_HREF;
    config.pin_sccb_sda = CAM_PIN_SIOD;
    config.pin_sccb_scl = CAM_PIN_SIOC;
    config.pin_pwdn = CAM_PIN_PWDN;
    config.pin_reset = CAM_PIN_RESET;
    config.xclk_freq_hz = CAM_XCLK_FREQ;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;

    // Start with lower resolution for reliability
    config.frame_size = DEFAULT_FRAME_SIZE;
    config.jpeg_quality = DEFAULT_JPEG_QUALITY;
    config.fb_count = DEFAULT_FB_COUNT;
    config.fb_location = CAMERA_FB_IN_PSRAM;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        LOG_ERROR(TAG, "Camera init failed: 0x%x", err);
        return false;
    }

    initialized_ = true;
    LOG_INFO(TAG, "Camera initialized successfully");
    return true;
}

camera_fb_t* CameraManager::capture() {
    if (!initialized_) {
        LOG_ERROR(TAG, "Camera not initialized");
        return nullptr;
    }

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        LOG_ERROR(TAG, "Frame capture failed");
    }
    return fb;
}

void CameraManager::release(camera_fb_t* fb) {
    if (fb) {
        esp_camera_fb_return(fb);
    }
}

bool CameraManager::applyConfig(const CameraConfig& config) {
    sensor_t* sensor = getSensor();
    if (!sensor) {
        return false;
    }

    sensor->set_framesize(sensor, config.frameSize);
    sensor->set_quality(sensor, config.jpegQuality);
    sensor->set_brightness(sensor, config.brightness);
    sensor->set_contrast(sensor, config.contrast);
    sensor->set_saturation(sensor, config.saturation);
    sensor->set_sharpness(sensor, config.sharpness);
    sensor->set_denoise(sensor, config.denoise);
    sensor->set_special_effect(sensor, config.specialEffect);
    sensor->set_whitebal(sensor, config.whiteBalance ? 1 : 0);
    sensor->set_awb_gain(sensor, config.awbGain ? 1 : 0);
    sensor->set_wb_mode(sensor, config.wbMode);
    sensor->set_exposure_ctrl(sensor, config.exposureCtrl ? 1 : 0);
    sensor->set_aec2(sensor, config.aec2 ? 1 : 0);
    sensor->set_ae_level(sensor, config.aeLevel);
    sensor->set_aec_value(sensor, config.aecValue);
    sensor->set_gain_ctrl(sensor, config.gainCtrl ? 1 : 0);
    sensor->set_agc_gain(sensor, config.agcGain);
    sensor->set_gainceiling(sensor, (gainceiling_t)config.gainCeiling);
    sensor->set_bpc(sensor, config.bpc ? 1 : 0);
    sensor->set_wpc(sensor, config.wpc ? 1 : 0);
    sensor->set_raw_gma(sensor, config.rawGma ? 1 : 0);
    sensor->set_lenc(sensor, config.lenc ? 1 : 0);
    sensor->set_hmirror(sensor, config.hMirror ? 1 : 0);
    sensor->set_vflip(sensor, config.vFlip ? 1 : 0);
    sensor->set_dcw(sensor, config.dcw ? 1 : 0);
    sensor->set_colorbar(sensor, config.colorbar ? 1 : 0);

    LOG_INFO(TAG, "Camera config applied");
    return true;
}

bool CameraManager::getConfig(CameraConfig& config) {
    sensor_t* sensor = getSensor();
    if (!sensor) {
        return false;
    }

    config.frameSize = (framesize_t)sensor->status.framesize;
    config.jpegQuality = sensor->status.quality;
    config.brightness = sensor->status.brightness;
    config.contrast = sensor->status.contrast;
    config.saturation = sensor->status.saturation;
    config.sharpness = sensor->status.sharpness;
    config.denoise = sensor->status.denoise;
    config.specialEffect = sensor->status.special_effect;
    config.whiteBalance = sensor->status.awb;
    config.awbGain = sensor->status.awb_gain;
    config.wbMode = sensor->status.wb_mode;
    config.exposureCtrl = sensor->status.aec;
    config.aec2 = sensor->status.aec2;
    config.aeLevel = sensor->status.ae_level;
    config.aecValue = sensor->status.aec_value;
    config.gainCtrl = sensor->status.agc;
    config.agcGain = sensor->status.agc_gain;
    config.gainCeiling = sensor->status.gainceiling;
    config.bpc = sensor->status.bpc;
    config.wpc = sensor->status.wpc;
    config.rawGma = sensor->status.raw_gma;
    config.lenc = sensor->status.lenc;
    config.hMirror = sensor->status.hmirror;
    config.vFlip = sensor->status.vflip;
    config.dcw = sensor->status.dcw;
    config.colorbar = sensor->status.colorbar;

    return true;
}

bool CameraManager::setFrameSize(framesize_t size) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_framesize(sensor, size) == 0;
}

bool CameraManager::setQuality(uint8_t quality) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_quality(sensor, quality) == 0;
}

bool CameraManager::setBrightness(int8_t brightness) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_brightness(sensor, brightness) == 0;
}

bool CameraManager::setContrast(int8_t contrast) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_contrast(sensor, contrast) == 0;
}

bool CameraManager::setSaturation(int8_t saturation) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_saturation(sensor, saturation) == 0;
}

bool CameraManager::setSharpness(int8_t sharpness) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_sharpness(sensor, sharpness) == 0;
}

bool CameraManager::setHMirror(bool enable) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_hmirror(sensor, enable ? 1 : 0) == 0;
}

bool CameraManager::setVFlip(bool enable) {
    sensor_t* sensor = getSensor();
    if (!sensor) return false;
    return sensor->set_vflip(sensor, enable ? 1 : 0) == 0;
}

void CameraManager::setFlash(bool on) {
    flashOn_ = on;
    digitalWrite(LED_FLASH_PIN, on ? HIGH : LOW);
    LOG_DEBUG(TAG, "Flash %s", on ? "ON" : "OFF");
}

bool CameraManager::getFlash() const {
    return flashOn_;
}

void CameraManager::toggleFlash() {
    setFlash(!flashOn_);
}

sensor_t* CameraManager::getSensor() {
    if (!initialized_) {
        LOG_ERROR(TAG, "Camera not initialized");
        return nullptr;
    }
    return esp_camera_sensor_get();
}
