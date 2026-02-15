// IMPORTANT: This file must NOT include ESPAsyncWebServer headers
// to avoid symbol conflicts with esp_http_server.h

#include <esp_http_server.h>
#include "network/MjpegServer.h"
#include "utils/Logger.h"
#include <esp_camera.h>

static const char* TAG = "MJPEG";

// MJPEG boundary - must match what Python client expects
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// Global pointer for static handler
static MjpegServer* g_mjpegServer = nullptr;

// Forward declaration
static esp_err_t streamHandler(httpd_req_t* req);

MjpegServer::MjpegServer(CameraManager& camera)
    : camera_(camera) {
    g_mjpegServer = this;
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
    LOG_INFO(TAG, "MJPEG server started on port %d", port);
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

    // Set content type for MJPEG stream
    httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");
    httpd_resp_set_hdr(req, "X-Framerate", "25");

    char partBuf[64];
    esp_err_t res = ESP_OK;
    uint32_t lastFrameTime = 0;
    uint32_t frameCount = 0;
    uint32_t errorCount = 0;
    const uint32_t maxConsecutiveErrors = 10;

    while (res == ESP_OK) {
        // Rate limit to ~25 FPS max
        uint32_t now = millis();
        if (now - lastFrameTime < 40) {
            vTaskDelay(pdMS_TO_TICKS(40 - (now - lastFrameTime)));
        }
        lastFrameTime = millis();

        // Capture frame
        camera_fb_t* fb = server->getCamera().capture();
        if (!fb) {
            errorCount++;
            LOG_WARN(TAG, "Capture failed (%u consecutive)", errorCount);
            if (errorCount >= maxConsecutiveErrors) {
                LOG_ERROR(TAG, "Too many capture failures, ending stream");
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Validate JPEG
        if (fb->len < 100 || fb->buf[0] != 0xFF || fb->buf[1] != 0xD8) {
            server->getCamera().release(fb);
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

        // Send boundary
        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        if (res != ESP_OK) {
            server->getCamera().release(fb);
            break;
        }

        // Send content-type and length header
        size_t hlen = snprintf(partBuf, sizeof(partBuf), STREAM_PART, fb->len);
        res = httpd_resp_send_chunk(req, partBuf, hlen);
        if (res != ESP_OK) {
            server->getCamera().release(fb);
            break;
        }

        // Send JPEG data
        res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
        server->getCamera().release(fb);

        if (res != ESP_OK) {
            break;
        }

        // Log stats periodically
        if (frameCount % 100 == 0) {
            LOG_DEBUG(TAG, "Streamed %u frames", frameCount);
        }
    }

    // Stream ended
    server->decrementStreams();
    LOG_INFO(TAG, "Stream ended after %u frames, active: %d", frameCount, server->getActiveStreams());

    return res;
}
