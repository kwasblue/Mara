#include "network/StreamHandler.h"
#include "network/WebServer.h"
#include "utils/Logger.h"
#include <esp_camera.h>

static const char* TAG = "Capture";

StreamHandler::StreamHandler(CameraManager& camera)
    : camera_(camera) {}

void StreamHandler::registerHandlers(AsyncWebServer& server) {
    // Single JPEG capture
    server.on("/jpg", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleCapture(request);
    });

    LOG_INFO(TAG, "Capture handler registered on /jpg");
}

void StreamHandler::handleCapture(AsyncWebServerRequest* request) {
    camera_fb_t* fb = camera_.capture();
    if (!fb) {
        WebServerManager::sendError(request, 500, "Camera capture failed");
        return;
    }

    // Validate JPEG structure
    if (fb->len < 4 || fb->buf[0] != 0xFF || fb->buf[1] != 0xD8) {
        LOG_ERROR(TAG, "Invalid JPEG: bad header");
        camera_.release(fb);
        WebServerManager::sendError(request, 500, "Invalid frame data");
        return;
    }

    // Copy frame to PSRAM for async send
    size_t jpegLen = fb->len;
    uint8_t* jpegCopy = (uint8_t*)ps_malloc(jpegLen);
    if (!jpegCopy) {
        jpegCopy = (uint8_t*)malloc(jpegLen);
    }

    if (!jpegCopy) {
        LOG_ERROR(TAG, "Failed to allocate %u bytes for JPEG copy", jpegLen);
        camera_.release(fb);
        WebServerManager::sendError(request, 500, "Memory allocation failed");
        return;
    }

    memcpy(jpegCopy, fb->buf, jpegLen);
    camera_.release(fb);

    // Create response that sends data in chunks
    AsyncWebServerResponse* response = request->beginResponse(
        "image/jpeg",
        jpegLen,
        [jpegCopy, jpegLen](uint8_t* buffer, size_t maxLen, size_t index) -> size_t {
            if (index >= jpegLen) {
                return 0;
            }
            size_t remaining = jpegLen - index;
            size_t toWrite = (remaining < maxLen) ? remaining : maxLen;
            memcpy(buffer, jpegCopy + index, toWrite);
            return toWrite;
        }
    );

    // Free buffer when request completes
    request->onDisconnect([jpegCopy]() {
        free(jpegCopy);
    });

    response->setCode(200);
    response->addHeader("Content-Disposition", "inline; filename=capture.jpg");
    response->addHeader("Cache-Control", "no-cache, no-store, must-revalidate");
    WebServerManager::addCORSHeaders(response);
    request->send(response);
}
