#pragma once

#include <Arduino.h>
#include "camera/CameraManager.h"
#include "config/DefaultSettings.h"

/**
 * Standalone MJPEG streaming server using ESP-IDF HTTP server.
 * Kept separate from ESPAsyncWebServer to avoid symbol conflicts.
 */
class MjpegServer {
public:
    MjpegServer(CameraManager& camera);
    ~MjpegServer();

    // Start the MJPEG server on specified port
    bool start(uint16_t port = 81);

    // Stop the server
    void stop();

    // Check if server is running
    bool isRunning() const { return running_; }

    // Get active stream count
    uint8_t getActiveStreams() const { return activeStreams_; }

    // Stream count management (for static handler)
    bool canAcceptStream() const { return activeStreams_ < MAX_STREAM_CLIENTS; }
    void incrementStreams() { activeStreams_++; }
    void decrementStreams() { if (activeStreams_ > 0) activeStreams_--; }

    // Camera access (for static handler)
    CameraManager& getCamera() { return camera_; }

private:
    CameraManager& camera_;
    void* serverHandle_ = nullptr;  // httpd_handle_t
    volatile uint8_t activeStreams_ = 0;
    bool running_ = false;
};
