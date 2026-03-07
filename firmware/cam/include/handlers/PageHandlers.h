#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include "camera/CameraManager.h"
#include "network/WiFiManager.h"

class PageHandlers {
public:
    PageHandlers(CameraManager& camera, WiFiManager& wifi);

    // Register page endpoints
    void registerHandlers(AsyncWebServer& server);

private:
    CameraManager& camera_;
    WiFiManager& wifi_;

    void handleRoot(AsyncWebServerRequest* request);
    void handleConfig(AsyncWebServerRequest* request);
};

// HTML content (stored in PROGMEM)
extern const char INDEX_HTML[] PROGMEM;
extern const char CONFIG_HTML[] PROGMEM;
