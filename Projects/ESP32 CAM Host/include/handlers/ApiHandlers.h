#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "camera/CameraManager.h"
#include "camera/MotionDetector.h"
#include "network/WiFiManager.h"
#include "storage/ConfigStore.h"
#include "security/AuthMiddleware.h"

class ApiHandlers {
public:
    ApiHandlers(CameraManager& camera, MotionDetector& motion,
                WiFiManager& wifi, ConfigStore& config, AuthMiddleware& auth);

    // Register API endpoints
    void registerHandlers(AsyncWebServer& server);

private:
    CameraManager& camera_;
    MotionDetector& motion_;
    WiFiManager& wifi_;
    ConfigStore& config_;
    AuthMiddleware& auth_;

    // Status endpoints
    void handleStatus(AsyncWebServerRequest* request);

    // Camera config endpoints
    void handleGetCameraConfig(AsyncWebServerRequest* request);
    void handleSetCameraConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len);

    // Network config endpoints
    void handleGetNetworkConfig(AsyncWebServerRequest* request);
    void handleSetNetworkConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len);

    // Motion config endpoints
    void handleGetMotionConfig(AsyncWebServerRequest* request);
    void handleSetMotionConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len);

    // Action endpoints
    void handleFlash(AsyncWebServerRequest* request);
    void handleReboot(AsyncWebServerRequest* request);
    void handleFactoryReset(AsyncWebServerRequest* request);
};
