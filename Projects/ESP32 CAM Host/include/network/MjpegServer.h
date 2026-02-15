#pragma once

#include <Arduino.h>
#include "camera/CameraManager.h"
#include "config/DefaultSettings.h"

/**
 * Streaming statistics for performance monitoring.
 */
struct StreamStats {
    uint32_t totalFrames = 0;       // Total frames sent (all clients)
    uint32_t droppedFrames = 0;     // Frames dropped due to timing
    uint32_t errorFrames = 0;       // Frames with capture/encode errors
    float currentFps = 0.0f;        // Current FPS (rolling average)
    float avgLatencyMs = 0.0f;      // Average frame latency (capture + send)
    uint32_t totalBytes = 0;        // Total bytes sent
    uint32_t uptimeSeconds = 0;     // Server uptime
    uint8_t activeClients = 0;      // Current active streams
    uint8_t currentQuality = 0;     // Current JPEG quality (with adjustments)
};

/**
 * Resolution presets for quick bandwidth switching.
 */
enum class StreamPreset : uint8_t {
    PRESET_HIGH = 0,    // VGA 640x480, quality 10
    PRESET_MEDIUM = 1,  // CIF 400x296, quality 12
    PRESET_LOW = 2,     // QVGA 320x240, quality 15
    PRESET_MINIMAL = 3  // QQVGA 160x120, quality 20
};

/**
 * Standalone MJPEG streaming server using ESP-IDF HTTP server.
 * Kept separate from ESPAsyncWebServer to avoid symbol conflicts.
 *
 * Optimizations:
 * - Combined network writes (single send per frame)
 * - Adaptive frame rate (no fixed delays)
 * - Dynamic JPEG quality based on client count
 * - Frame skipping under load
 * - TCP tuning for streaming
 * - Streaming statistics
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
    void incrementStreams();
    void decrementStreams();

    // Camera access (for static handler)
    CameraManager& getCamera() { return camera_; }

    // ===== Statistics =====

    // Get current streaming statistics
    StreamStats getStats() const;

    // Reset statistics
    void resetStats();

    // Update stats (called from stream handler)
    void recordFrame(uint32_t sizeBytes, uint32_t latencyMs, bool dropped = false, bool error = false);

    // ===== Dynamic Quality =====

    // Get effective JPEG quality (base + adjustments for client count)
    uint8_t getEffectiveQuality() const;

    // Enable/disable dynamic quality scaling
    void setQualityScaling(bool enabled) { qualityScalingEnabled_ = enabled; }
    bool isQualityScalingEnabled() const { return qualityScalingEnabled_; }

    // ===== Resolution Presets =====

    // Apply a resolution preset
    bool applyPreset(StreamPreset preset);

    // Get current preset (or HIGH if custom)
    StreamPreset getCurrentPreset() const { return currentPreset_; }

    // ===== Frame Rate Control =====

    // Set target FPS (0 = unlimited)
    void setTargetFps(uint8_t fps) { targetFps_ = fps; }
    uint8_t getTargetFps() const { return targetFps_; }

    // Get minimum frame interval in ms
    uint32_t getMinFrameIntervalMs() const;

private:
    CameraManager& camera_;
    void* serverHandle_ = nullptr;  // httpd_handle_t
    volatile uint8_t activeStreams_ = 0;
    bool running_ = false;

    // Statistics (volatile for thread safety)
    volatile uint32_t totalFrames_ = 0;
    volatile uint32_t droppedFrames_ = 0;
    volatile uint32_t errorFrames_ = 0;
    volatile uint32_t totalBytes_ = 0;
    uint32_t startTime_ = 0;

    // FPS calculation (rolling average)
    static constexpr int FPS_SAMPLE_COUNT = 10;
    uint32_t frameTimes_[FPS_SAMPLE_COUNT] = {0};
    uint8_t frameTimeIndex_ = 0;
    uint32_t lastFrameTime_ = 0;

    // Latency tracking
    uint32_t latencySum_ = 0;
    uint32_t latencyCount_ = 0;

    // Quality scaling
    bool qualityScalingEnabled_ = STREAM_QUALITY_SCALING;
    uint8_t baseQuality_ = DEFAULT_JPEG_QUALITY;

    // Resolution preset
    StreamPreset currentPreset_ = StreamPreset::PRESET_HIGH;

    // Frame rate control
    uint8_t targetFps_ = STREAM_TARGET_FPS;
};
