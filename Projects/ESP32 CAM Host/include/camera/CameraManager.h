#pragma once

#include <Arduino.h>
#include "esp_camera.h"
#include "config/BoardConfig.h"
#include "storage/ConfigStore.h"

class CameraManager {
public:
    CameraManager();

    // Initialize camera hardware
    bool begin();

    // Capture a JPEG frame
    camera_fb_t* capture();

    // Return frame buffer to pool
    void release(camera_fb_t* fb);

    // Apply settings from config
    bool applyConfig(const CameraConfig& config);

    // Get current sensor settings
    bool getConfig(CameraConfig& config);

    // Individual setting controls
    bool setFrameSize(framesize_t size);
    bool setQuality(uint8_t quality);
    bool setBrightness(int8_t brightness);
    bool setContrast(int8_t contrast);
    bool setSaturation(int8_t saturation);
    bool setSharpness(int8_t sharpness);
    bool setHMirror(bool enable);
    bool setVFlip(bool enable);

    // Flash LED control
    void setFlash(bool on);
    bool getFlash() const;
    void toggleFlash();

    // Check if camera is initialized
    bool isInitialized() const { return initialized_; }

    // Get sensor pointer for advanced operations
    sensor_t* getSensor();

private:
    bool initialized_ = false;
    bool flashOn_ = false;
};
