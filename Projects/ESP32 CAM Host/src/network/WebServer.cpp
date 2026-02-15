#include "network/WebServer.h"
#include "utils/Logger.h"

static const char* TAG = "WebServer";

WebServerManager::WebServerManager(uint16_t port)
    : server_(port) {}

bool WebServerManager::begin() {
    LOG_INFO(TAG, "Initializing web server");

    setupDefaultHandlers();
    server_.begin();

    LOG_INFO(TAG, "Web server started");
    return true;
}

void WebServerManager::setupDefaultHandlers() {
    // Handle OPTIONS for CORS preflight
    server_.onNotFound([](AsyncWebServerRequest* request) {
        if (request->method() == HTTP_OPTIONS) {
            AsyncWebServerResponse* response = request->beginResponse(204);
            addCORSHeaders(response);
            request->send(response);
        } else {
            request->send(404, "text/plain", "Not Found");
        }
    });
}

void WebServerManager::addCORSHeaders(AsyncWebServerResponse* response) {
    response->addHeader("Access-Control-Allow-Origin", "*");
    response->addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
    response->addHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
    response->addHeader("Access-Control-Max-Age", "86400");
}

void WebServerManager::sendJson(AsyncWebServerRequest* request, int code, const String& json) {
    AsyncWebServerResponse* response = request->beginResponse(code, "application/json", json);
    addCORSHeaders(response);
    request->send(response);
}

void WebServerManager::sendError(AsyncWebServerRequest* request, int code, const String& message) {
    String json = "{\"error\":\"" + message + "\"}";
    sendJson(request, code, json);
}

void WebServerManager::sendSuccess(AsyncWebServerRequest* request, const String& message) {
    String json = "{\"status\":\"" + message + "\"}";
    sendJson(request, 200, json);
}
