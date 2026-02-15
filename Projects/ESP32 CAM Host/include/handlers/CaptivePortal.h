#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include "storage/ConfigStore.h"
#include "network/WiFiManager.h"

class CaptivePortal {
public:
    CaptivePortal(ConfigStore& config, WiFiManager& wifi);

    // Register captive portal endpoints
    void registerHandlers(AsyncWebServer& server);

    // Check if we're in captive portal mode
    bool isActive() const { return active_; }

    // Set active state
    void setActive(bool active) { active_ = active; }

private:
    ConfigStore& config_;
    WiFiManager& wifi_;
    bool active_ = false;

    void handlePortalPage(AsyncWebServerRequest* request);
    void handleSaveConfig(AsyncWebServerRequest* request);
    void handleScan(AsyncWebServerRequest* request);
};

extern const char CAPTIVE_HTML[] PROGMEM;
