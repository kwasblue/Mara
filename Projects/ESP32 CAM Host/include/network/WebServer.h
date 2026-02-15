#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include "security/AuthMiddleware.h"

class WebServerManager {
public:
    WebServerManager(uint16_t port = 80);

    // Initialize server
    bool begin();

    // Get server instance for adding handlers
    AsyncWebServer& getServer() { return server_; }

    // Get auth middleware
    AuthMiddleware& getAuth() { return auth_; }

    // Add CORS headers to response
    static void addCORSHeaders(AsyncWebServerResponse* response);

    // Common response helpers
    static void sendJson(AsyncWebServerRequest* request, int code, const String& json);
    static void sendError(AsyncWebServerRequest* request, int code, const String& message);
    static void sendSuccess(AsyncWebServerRequest* request, const String& message = "OK");

private:
    AsyncWebServer server_;
    AuthMiddleware auth_;

    void setupDefaultHandlers();
};
