#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include <Update.h>

class OTAHandler {
public:
    OTAHandler();

    // Register OTA endpoints
    void registerHandlers(AsyncWebServer& server, bool requireAuth = true);

    // Check if update is in progress
    bool isUpdating() const { return updating_; }

    // Get update progress (0-100)
    uint8_t getProgress() const { return progress_; }

    // Get last error message
    const String& getError() const { return error_; }

private:
    bool updating_ = false;
    uint8_t progress_ = 0;
    String error_;
    size_t totalSize_ = 0;
    size_t receivedSize_ = 0;

    void handleUploadPage(AsyncWebServerRequest* request);
    void handleUpload(AsyncWebServerRequest* request, const String& filename,
                     size_t index, uint8_t* data, size_t len, bool final);
    void handleUploadComplete(AsyncWebServerRequest* request);
};
