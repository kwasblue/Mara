#include "handlers/ApiHandlers.h"
#include "network/WebServer.h"
#include "utils/Logger.h"

static const char* TAG = "API";

ApiHandlers::ApiHandlers(CameraManager& camera, MotionDetector& motion,
                         WiFiManager& wifi, ConfigStore& config, AuthMiddleware& auth)
    : camera_(camera), motion_(motion), wifi_(wifi), config_(config), auth_(auth) {}

void ApiHandlers::registerHandlers(AsyncWebServer& server) {
    // Status (public)
    server.on("/api/status", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleStatus(request);
    });

    // Camera config
    server.on("/api/camera/config", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleGetCameraConfig(request);
    });

    server.on("/api/camera/config", HTTP_POST,
        [](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (index == 0 && len == total) {
                handleSetCameraConfig(request, data, len);
            }
        }
    );

    // Network config (protected)
    server.on("/api/network/config", HTTP_GET, [this](AsyncWebServerRequest* request) {
        if (!auth_.authenticate(request)) {
            auth_.sendUnauthorized(request);
            return;
        }
        handleGetNetworkConfig(request);
    });

    server.on("/api/network/config", HTTP_POST,
        [this](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (!auth_.authenticate(request)) {
                auth_.sendUnauthorized(request);
                return;
            }
            if (index == 0 && len == total) {
                handleSetNetworkConfig(request, data, len);
            }
        }
    );

    // Motion config
    server.on("/api/motion/config", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleGetMotionConfig(request);
    });

    server.on("/api/motion/config", HTTP_POST,
        [](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (index == 0 && len == total) {
                handleSetMotionConfig(request, data, len);
            }
        }
    );

    // Flash toggle (public)
    server.on("/flash", HTTP_POST, [this](AsyncWebServerRequest* request) {
        handleFlash(request);
    });

    // Reboot (protected)
    server.on("/api/reboot", HTTP_POST, [this](AsyncWebServerRequest* request) {
        if (!auth_.authenticate(request)) {
            auth_.sendUnauthorized(request);
            return;
        }
        handleReboot(request);
    });

    // Factory reset (protected)
    server.on("/api/factory-reset", HTTP_POST, [this](AsyncWebServerRequest* request) {
        if (!auth_.authenticate(request)) {
            auth_.sendUnauthorized(request);
            return;
        }
        handleFactoryReset(request);
    });

    LOG_INFO(TAG, "API handlers registered");
}

void ApiHandlers::handleStatus(AsyncWebServerRequest* request) {
    JsonDocument doc;

    doc["hostname"] = wifi_.getHostname();
    doc["ip"] = wifi_.getIP().toString();
    doc["rssi"] = wifi_.getRSSI();
    doc["mac"] = wifi_.getMacAddress();
    doc["freeHeap"] = ESP.getFreeHeap();
    doc["uptime"] = millis() / 1000;
    doc["flashOn"] = camera_.getFlash();
    doc["apMode"] = wifi_.isAPMode();

    if (motion_.isEnabled()) {
        doc["motionEnabled"] = true;
        doc["lastMotion"] = motion_.getLastMotionTime();
    }

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleGetCameraConfig(AsyncWebServerRequest* request) {
    CameraConfig camConfig;
    camera_.getConfig(camConfig);

    JsonDocument doc;
    doc["frameSize"] = (int)camConfig.frameSize;
    doc["quality"] = camConfig.jpegQuality;
    doc["brightness"] = camConfig.brightness;
    doc["contrast"] = camConfig.contrast;
    doc["saturation"] = camConfig.saturation;
    doc["sharpness"] = camConfig.sharpness;
    doc["hmirror"] = camConfig.hMirror;
    doc["vflip"] = camConfig.vFlip;
    doc["whiteBalance"] = camConfig.whiteBalance;
    doc["awbGain"] = camConfig.awbGain;
    doc["wbMode"] = camConfig.wbMode;
    doc["exposureCtrl"] = camConfig.exposureCtrl;
    doc["aecValue"] = camConfig.aecValue;
    doc["gainCtrl"] = camConfig.gainCtrl;
    doc["agcGain"] = camConfig.agcGain;

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleSetCameraConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, data, len);

    if (error) {
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    CameraConfig camConfig;
    camera_.getConfig(camConfig);

    // Update only provided fields
    if (doc.containsKey("frameSize")) {
        camConfig.frameSize = (framesize_t)doc["frameSize"].as<int>();
        camera_.setFrameSize(camConfig.frameSize);
    }
    if (doc.containsKey("quality")) {
        camConfig.jpegQuality = doc["quality"];
        camera_.setQuality(camConfig.jpegQuality);
    }
    if (doc.containsKey("brightness")) {
        camConfig.brightness = doc["brightness"];
        camera_.setBrightness(camConfig.brightness);
    }
    if (doc.containsKey("contrast")) {
        camConfig.contrast = doc["contrast"];
        camera_.setContrast(camConfig.contrast);
    }
    if (doc.containsKey("saturation")) {
        camConfig.saturation = doc["saturation"];
        camera_.setSaturation(camConfig.saturation);
    }
    if (doc.containsKey("sharpness")) {
        camConfig.sharpness = doc["sharpness"];
        camera_.setSharpness(camConfig.sharpness);
    }
    if (doc.containsKey("hmirror")) {
        camConfig.hMirror = doc["hmirror"];
        camera_.setHMirror(camConfig.hMirror);
    }
    if (doc.containsKey("vflip")) {
        camConfig.vFlip = doc["vflip"];
        camera_.setVFlip(camConfig.vFlip);
    }

    // Save to NVS
    config_.saveCameraConfig(camConfig);

    WebServerManager::sendSuccess(request, "Camera config updated");
}

void ApiHandlers::handleGetNetworkConfig(AsyncWebServerRequest* request) {
    NetworkConfig netConfig;
    config_.loadNetworkConfig(netConfig);

    JsonDocument doc;
    doc["ssid"] = netConfig.ssid;
    doc["hostname"] = netConfig.hostname;
    doc["apSsid"] = netConfig.apSsid;
    doc["apChannel"] = netConfig.apChannel;
    doc["configured"] = netConfig.configured;
    // Don't send passwords

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleSetNetworkConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, data, len);

    if (error) {
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    NetworkConfig netConfig;
    config_.loadNetworkConfig(netConfig);

    if (doc.containsKey("ssid")) {
        strncpy(netConfig.ssid, doc["ssid"] | "", sizeof(netConfig.ssid) - 1);
    }
    if (doc.containsKey("password")) {
        strncpy(netConfig.password, doc["password"] | "", sizeof(netConfig.password) - 1);
    }
    if (doc.containsKey("hostname")) {
        strncpy(netConfig.hostname, doc["hostname"] | "", sizeof(netConfig.hostname) - 1);
    }
    if (doc.containsKey("apSsid")) {
        strncpy(netConfig.apSsid, doc["apSsid"] | "", sizeof(netConfig.apSsid) - 1);
    }
    if (doc.containsKey("apPassword")) {
        strncpy(netConfig.apPassword, doc["apPassword"] | "", sizeof(netConfig.apPassword) - 1);
    }

    netConfig.configured = strlen(netConfig.ssid) > 0;
    config_.saveNetworkConfig(netConfig);

    WebServerManager::sendSuccess(request, "Network config updated. Reboot to apply.");
}

void ApiHandlers::handleGetMotionConfig(AsyncWebServerRequest* request) {
    MotionConfig motConfig;
    config_.loadMotionConfig(motConfig);

    JsonDocument doc;
    doc["enabled"] = motConfig.enabled;
    doc["sensitivity"] = motConfig.sensitivity;
    doc["threshold"] = motConfig.threshold;
    doc["cooldownMs"] = motConfig.cooldownMs;

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleSetMotionConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, data, len);

    if (error) {
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    MotionConfig motConfig;
    config_.loadMotionConfig(motConfig);

    if (doc.containsKey("enabled")) {
        motConfig.enabled = doc["enabled"];
    }
    if (doc.containsKey("sensitivity")) {
        motConfig.sensitivity = doc["sensitivity"];
    }
    if (doc.containsKey("threshold")) {
        motConfig.threshold = doc["threshold"];
    }
    if (doc.containsKey("cooldownMs")) {
        motConfig.cooldownMs = doc["cooldownMs"];
    }

    config_.saveMotionConfig(motConfig);
    motion_.configure(motConfig);

    WebServerManager::sendSuccess(request, "Motion config updated");
}

void ApiHandlers::handleFlash(AsyncWebServerRequest* request) {
    camera_.toggleFlash();

    JsonDocument doc;
    doc["flash"] = camera_.getFlash();

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleReboot(AsyncWebServerRequest* request) {
    WebServerManager::sendSuccess(request, "Rebooting...");
    delay(500);
    ESP.restart();
}

void ApiHandlers::handleFactoryReset(AsyncWebServerRequest* request) {
    config_.factoryReset();
    WebServerManager::sendSuccess(request, "Factory reset complete. Rebooting...");
    delay(500);
    ESP.restart();
}
