#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include "camera/CameraManager.h"
#include "config/DefaultSettings.h"

/**
 * Handles single JPEG capture endpoint via ESPAsyncWebServer.
 * MJPEG streaming is handled by MjpegServer (separate to avoid conflicts).
 */
class StreamHandler {
public:
    StreamHandler(CameraManager& camera);

    // Register /jpg endpoint with AsyncWebServer
    void registerHandlers(AsyncWebServer& server);

private:
    CameraManager& camera_;

    // Single JPEG capture handler
    void handleCapture(AsyncWebServerRequest* request);
};
