#include "handlers/ApiHandlers.h"
#include "network/WebServer.h"
#include "utils/Logger.h"

static const char* TAG = "API";

ApiHandlers::ApiHandlers(CameraManager& camera, MotionDetector& motion,
                         WiFiManager& wifi, ConfigStore& config, AuthMiddleware& auth,
                         MjpegServer* mjpegServer)
    : camera_(camera), motion_(motion), wifi_(wifi), config_(config), auth_(auth),
      mjpegServer_(mjpegServer) {}

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

    // Streaming stats (public)
    server.on("/api/stream/stats", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleStreamStats(request);
    });

    // Streaming preset (public)
    server.on("/api/stream/preset", HTTP_POST,
        [](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (index == 0 && len == total) {
                handleStreamPreset(request, data, len);
            }
        }
    );

    // Streaming config (FPS, quality scaling, etc.)
    server.on("/api/stream/config", HTTP_POST,
        [](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (index == 0 && len == total) {
                handleStreamConfig(request, data, len);
            }
        }
    );

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

void ApiHandlers::handleStreamStats(AsyncWebServerRequest* request) {
    JsonDocument doc;

    if (mjpegServer_) {
        StreamStats stats = mjpegServer_->getStats();
        doc["totalFrames"] = stats.totalFrames;
        doc["droppedFrames"] = stats.droppedFrames;
        doc["errorFrames"] = stats.errorFrames;
        doc["currentFps"] = stats.currentFps;
        doc["avgLatencyMs"] = stats.avgLatencyMs;
        doc["totalBytes"] = stats.totalBytes;
        doc["uptimeSeconds"] = stats.uptimeSeconds;
        doc["activeClients"] = stats.activeClients;
        doc["currentQuality"] = stats.currentQuality;
        doc["targetFps"] = mjpegServer_->getTargetFps();
        doc["qualityScaling"] = mjpegServer_->isQualityScalingEnabled();
        doc["preset"] = (int)mjpegServer_->getCurrentPreset();
    } else {
        doc["error"] = "MJPEG server not available";
    }

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void ApiHandlers::handleStreamPreset(AsyncWebServerRequest* request, uint8_t* data, size_t len) {
    if (!mjpegServer_) {
        WebServerManager::sendError(request, 500, "MJPEG server not available");
        return;
    }

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, data, len);

    if (error) {
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    if (!doc.containsKey("preset")) {
        WebServerManager::sendError(request, 400, "Missing 'preset' field");
        return;
    }

    int presetValue = doc["preset"];
    if (presetValue < 0 || presetValue > 3) {
        WebServerManager::sendError(request, 400, "Invalid preset (0-3)");
        return;
    }

    StreamPreset preset = static_cast<StreamPreset>(presetValue);
    if (mjpegServer_->applyPreset(preset)) {
        JsonDocument response;
        response["preset"] = presetValue;
        response["presetName"] = presetValue == 0 ? "high" :
                                  presetValue == 1 ? "medium" :
                                  presetValue == 2 ? "low" : "minimal";

        String json;
        serializeJson(response, json);
        WebServerManager::sendJson(request, 200, json);
    } else {
        WebServerManager::sendError(request, 500, "Failed to apply preset");
    }
}

void ApiHandlers::handleStreamConfig(AsyncWebServerRequest* request, uint8_t* data, size_t len) {
    if (!mjpegServer_) {
        WebServerManager::sendError(request, 500, "MJPEG server not available");
        return;
    }

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, data, len);

    if (error) {
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    // Update target FPS
    if (doc.containsKey("targetFps")) {
        uint8_t fps = doc["targetFps"];
        mjpegServer_->setTargetFps(fps);
    }

    // Update quality scaling
    if (doc.containsKey("qualityScaling")) {
        bool enabled = doc["qualityScaling"];
        mjpegServer_->setQualityScaling(enabled);
    }

    // Reset stats if requested
    if (doc.containsKey("resetStats") && doc["resetStats"].as<bool>()) {
        mjpegServer_->resetStats();
    }

    WebServerManager::sendSuccess(request, "Stream config updated");
}
