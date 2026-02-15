// IMPORTANT: This file must NOT include ESPAsyncWebServer headers
// to avoid symbol conflicts with esp_http_server.h

#include <esp_http_server.h>
#include <esp_camera.h>
#include "network/MjpegServer.h"
#include "utils/Logger.h"

// TCP socket options (from lwip)
#ifndef TCP_NODELAY
#define TCP_NODELAY 1
#endif
#ifndef SOL_SOCKET
#define SOL_SOCKET 0xfff
#endif
#ifndef SO_SNDBUF
#define SO_SNDBUF 0x1001
#endif

// Forward declare setsockopt to avoid header conflicts
extern "C" int lwip_setsockopt(int s, int level, int optname, const void *optval, unsigned int optlen);

static const char* TAG = "MJPEG";

// MJPEG boundary - must match what Python client expects
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// Boundary and header sizes for pre-allocation
static constexpr size_t BOUNDARY_LEN = 38;  // strlen(STREAM_BOUNDARY)
static constexpr size_t HEADER_MAX_LEN = 64;

// Global pointer for static handler
static MjpegServer* g_mjpegServer = nullptr;

// Forward declaration
static esp_err_t streamHandler(httpd_req_t* req);

MjpegServer::MjpegServer(CameraManager& camera)
    : camera_(camera) {
    g_mjpegServer = this;
    startTime_ = millis();
}

MjpegServer::~MjpegServer() {
    stop();
    g_mjpegServer = nullptr;
}

bool MjpegServer::start(uint16_t port) {
    if (running_) {
        LOG_WARN(TAG, "Server already running");
        return true;
    }

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = port;
    config.ctrl_port = port + 1;
    config.max_open_sockets = MAX_STREAM_CLIENTS + 1;
    config.lru_purge_enable = true;
    config.recv_wait_timeout = 5;
    config.send_wait_timeout = 5;

    // Increase stack size for streaming
    config.stack_size = 8192;

    LOG_INFO(TAG, "Starting MJPEG server on port %d", port);

    httpd_handle_t server = nullptr;
    if (httpd_start(&server, &config) != ESP_OK) {
        LOG_ERROR(TAG, "Failed to start server");
        return false;
    }

    // Register stream URI handler
    httpd_uri_t streamUri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = streamHandler,
        .user_ctx = this
    };

    if (httpd_register_uri_handler(server, &streamUri) != ESP_OK) {
        LOG_ERROR(TAG, "Failed to register handler");
        httpd_stop(server);
        return false;
    }

    serverHandle_ = server;
    running_ = true;
    startTime_ = millis();
    LOG_INFO(TAG, "MJPEG server started on port %d (target %d FPS)", port, targetFps_);
    return true;
}

void MjpegServer::stop() {
    if (serverHandle_) {
        httpd_stop((httpd_handle_t)serverHandle_);
        serverHandle_ = nullptr;
        running_ = false;
        LOG_INFO(TAG, "MJPEG server stopped");
    }
}

void MjpegServer::incrementStreams() {
    activeStreams_++;

    // Apply dynamic quality when new client connects
    if (qualityScalingEnabled_ && activeStreams_ > 1) {
        uint8_t newQuality = getEffectiveQuality();
        camera_.setQuality(newQuality);
        LOG_INFO(TAG, "Client connected, quality adjusted to %d", newQuality);
    }
}

void MjpegServer::decrementStreams() {
    if (activeStreams_ > 0) {
        activeStreams_--;

        // Restore quality when clients disconnect
        if (qualityScalingEnabled_ && activeStreams_ <= 1) {
            camera_.setQuality(baseQuality_);
            LOG_DEBUG(TAG, "Client disconnected, quality restored to %d", baseQuality_);
        }
    }
}

// ===== Statistics =====

StreamStats MjpegServer::getStats() const {
    StreamStats stats;
    stats.totalFrames = totalFrames_;
    stats.droppedFrames = droppedFrames_;
    stats.errorFrames = errorFrames_;
    stats.totalBytes = totalBytes_;
    stats.uptimeSeconds = (millis() - startTime_) / 1000;
    stats.activeClients = activeStreams_;
    stats.currentQuality = getEffectiveQuality();

    // Calculate FPS from rolling average
    if (totalFrames_ >= FPS_SAMPLE_COUNT) {
        uint32_t totalTime = 0;
        for (int i = 0; i < FPS_SAMPLE_COUNT; i++) {
            totalTime += frameTimes_[i];
        }
        if (totalTime > 0) {
            stats.currentFps = (FPS_SAMPLE_COUNT * 1000.0f) / totalTime;
        }
    }

    // Calculate average latency
    if (latencyCount_ > 0) {
        stats.avgLatencyMs = (float)latencySum_ / latencyCount_;
    }

    return stats;
}

void MjpegServer::resetStats() {
    totalFrames_ = 0;
    droppedFrames_ = 0;
    errorFrames_ = 0;
    totalBytes_ = 0;
    latencySum_ = 0;
    latencyCount_ = 0;
    startTime_ = millis();
    memset(frameTimes_, 0, sizeof(frameTimes_));
    frameTimeIndex_ = 0;
}

void MjpegServer::recordFrame(uint32_t sizeBytes, uint32_t latencyMs, bool dropped, bool error) {
    if (dropped) {
        droppedFrames_++;
        return;
    }

    if (error) {
        errorFrames_++;
        return;
    }

    totalFrames_++;
    totalBytes_ += sizeBytes;

    // Update FPS tracking
    uint32_t now = millis();
    if (lastFrameTime_ > 0) {
        frameTimes_[frameTimeIndex_] = now - lastFrameTime_;
        frameTimeIndex_ = (frameTimeIndex_ + 1) % FPS_SAMPLE_COUNT;
    }
    lastFrameTime_ = now;

    // Update latency tracking (rolling average over last 100 frames)
    latencySum_ += latencyMs;
    latencyCount_++;
    if (latencyCount_ > 100) {
        latencySum_ = latencySum_ / 2;
        latencyCount_ = latencyCount_ / 2;
    }
}

// ===== Dynamic Quality =====

uint8_t MjpegServer::getEffectiveQuality() const {
    if (!qualityScalingEnabled_ || activeStreams_ <= 1) {
        return baseQuality_;
    }

    // Reduce quality for each additional client
    uint8_t reduction = (activeStreams_ - 1) * STREAM_QUALITY_PER_CLIENT;
    if (reduction > STREAM_MAX_QUALITY_REDUCTION) {
        reduction = STREAM_MAX_QUALITY_REDUCTION;
    }

    uint8_t newQuality = baseQuality_ + reduction;
    if (newQuality > 63) {
        newQuality = 63;  // Max JPEG quality value
    }

    return newQuality;
}

// ===== Resolution Presets =====

bool MjpegServer::applyPreset(StreamPreset preset) {
    framesize_t frameSize;
    uint8_t quality;

    switch (preset) {
        case StreamPreset::PRESET_HIGH:
            frameSize = FRAMESIZE_VGA;   // 640x480
            quality = 10;
            break;
        case StreamPreset::PRESET_MEDIUM:
            frameSize = FRAMESIZE_CIF;   // 400x296
            quality = 12;
            break;
        case StreamPreset::PRESET_LOW:
            frameSize = FRAMESIZE_QVGA;  // 320x240
            quality = 15;
            break;
        case StreamPreset::PRESET_MINIMAL:
            frameSize = FRAMESIZE_QQVGA; // 160x120
            quality = 20;
            break;
        default:
            return false;
    }

    if (camera_.setFrameSize(frameSize) && camera_.setQuality(quality)) {
        currentPreset_ = preset;
        baseQuality_ = quality;
        LOG_INFO(TAG, "Applied preset %d (quality %d)", (int)preset, quality);
        return true;
    }

    return false;
}

// ===== Frame Rate Control =====

uint32_t MjpegServer::getMinFrameIntervalMs() const {
    if (targetFps_ == 0) {
        return STREAM_MIN_FRAME_MS;
    }
    uint32_t interval = 1000 / targetFps_;
    return interval < STREAM_MIN_FRAME_MS ? STREAM_MIN_FRAME_MS : interval;
}

// ===== Stream Handler =====

static esp_err_t streamHandler(httpd_req_t* req) {
    MjpegServer* server = static_cast<MjpegServer*>(req->user_ctx);
    if (!server) {
        server = g_mjpegServer;
    }

    if (!server) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Server not initialized");
        return ESP_FAIL;
    }

    // Check max clients
    if (!server->canAcceptStream()) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Max streams reached");
        return ESP_FAIL;
    }

    server->incrementStreams();
    LOG_INFO(TAG, "Stream started, active: %d", server->getActiveStreams());

    // ===== TCP Tuning =====
    int sockfd = httpd_req_to_sockfd(req);
    if (sockfd >= 0) {
        // Disable Nagle's algorithm for lower latency
        int flag = 1;
        lwip_setsockopt(sockfd, 6, TCP_NODELAY, &flag, sizeof(flag));  // 6 = IPPROTO_TCP

        // Increase send buffer size
        int sendBufSize = 32768;  // 32KB
        lwip_setsockopt(sockfd, SOL_SOCKET, SO_SNDBUF, &sendBufSize, sizeof(sendBufSize));
    }

    // Set content type for MJPEG stream
    httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");
    httpd_resp_set_hdr(req, "X-Framerate", "30");

    // Pre-allocate combined buffer for boundary + header
    // Max frame size for VGA JPEG is ~100KB, we'll send that separately
    char headerBuf[BOUNDARY_LEN + HEADER_MAX_LEN];

    esp_err_t res = ESP_OK;
    uint32_t lastFrameTime = 0;
    uint32_t frameCount = 0;
    uint32_t errorCount = 0;
    const uint32_t maxConsecutiveErrors = 10;
    const uint32_t minFrameInterval = server->getMinFrameIntervalMs();

    while (res == ESP_OK) {
        uint32_t frameStart = millis();

        // ===== Adaptive Frame Rate =====
        // Only delay if we're ahead of schedule
        uint32_t elapsed = frameStart - lastFrameTime;
        if (lastFrameTime > 0 && elapsed < minFrameInterval) {
            vTaskDelay(pdMS_TO_TICKS(minFrameInterval - elapsed));
            frameStart = millis();
        }

        // ===== Capture Frame =====
        camera_fb_t* fb = server->getCamera().capture();
        uint32_t captureTime = millis() - frameStart;

        if (!fb) {
            errorCount++;
            server->recordFrame(0, 0, false, true);
            LOG_WARN(TAG, "Capture failed (%u consecutive)", errorCount);
            if (errorCount >= maxConsecutiveErrors) {
                LOG_ERROR(TAG, "Too many capture failures, ending stream");
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // ===== Frame Skipping Under Load =====
#if STREAM_ENABLE_FRAME_SKIP
        if (captureTime > STREAM_SKIP_THRESHOLD_MS) {
            server->getCamera().release(fb);
            server->recordFrame(0, captureTime, true, false);
            LOG_DEBUG(TAG, "Frame skipped (capture took %ums)", captureTime);
            lastFrameTime = millis();
            continue;
        }
#endif

        // ===== Validate JPEG =====
        if (fb->len < 100 || fb->buf[0] != 0xFF || fb->buf[1] != 0xD8) {
            server->getCamera().release(fb);
            server->recordFrame(0, 0, false, true);
            errorCount++;
            LOG_WARN(TAG, "Invalid JPEG, skipping");
            if (errorCount >= maxConsecutiveErrors) {
                break;
            }
            continue;
        }

        // Reset error count on success
        errorCount = 0;
        frameCount++;

        // ===== Combined Network Write =====
        // Build boundary + header in single buffer
        size_t headerLen = snprintf(headerBuf, sizeof(headerBuf),
            "\r\n--" PART_BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
            fb->len);

        // Send header (combined boundary + content-type + length)
        res = httpd_resp_send_chunk(req, headerBuf, headerLen);
        if (res != ESP_OK) {
            server->getCamera().release(fb);
            break;
        }

        // Send JPEG data
        res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);

        uint32_t totalLatency = millis() - frameStart;
        server->recordFrame(fb->len, totalLatency, false, false);

        server->getCamera().release(fb);
        lastFrameTime = millis();

        if (res != ESP_OK) {
            break;
        }

        // Log stats periodically
        if (frameCount % 100 == 0) {
            StreamStats stats = server->getStats();
            LOG_DEBUG(TAG, "Frames: %u, FPS: %.1f, Lat: %.0fms, Dropped: %u",
                stats.totalFrames, stats.currentFps, stats.avgLatencyMs, stats.droppedFrames);
        }
    }

    // Stream ended
    server->decrementStreams();
    StreamStats stats = server->getStats();
    LOG_INFO(TAG, "Stream ended after %u frames (FPS: %.1f, dropped: %u), active: %d",
        frameCount, stats.currentFps, stats.droppedFrames, server->getActiveStreams());

    return res;
}
