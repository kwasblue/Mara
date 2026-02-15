#include "security/AuthMiddleware.h"
#include "utils/Logger.h"

extern "C" {
#include "libb64/cdecode.h"
}

static const char* TAG = "Auth";

// Helper function to decode base64
static String decodeBase64(const String& encoded) {
    int inputLen = encoded.length();
    int outputLen = inputLen;  // Base64 decoded is smaller than encoded
    char* output = (char*)malloc(outputLen + 1);
    if (!output) return "";

    base64_decodestate state;
    base64_init_decodestate(&state);
    int len = base64_decode_block(encoded.c_str(), inputLen, output, &state);
    output[len] = '\0';

    String result(output);
    free(output);
    return result;
}

AuthMiddleware::AuthMiddleware() {
    memset(rateEntries_, 0, sizeof(rateEntries_));
}

void AuthMiddleware::setEnabled(bool enabled) {
    authEnabled_ = enabled;
    LOG_INFO(TAG, "Auth %s", enabled ? "enabled" : "disabled");
}

void AuthMiddleware::setRateLimit(uint8_t requestsPerMinute) {
    rateLimit_ = requestsPerMinute;
    LOG_INFO(TAG, "Rate limit set to %d req/min", requestsPerMinute);
}

bool AuthMiddleware::authenticate(AsyncWebServerRequest* request) {
    if (!authEnabled_) {
        return true;
    }

    if (!request->hasHeader("Authorization")) {
        LOG_DEBUG(TAG, "No Authorization header");
        return false;
    }

    String authHeader = request->header("Authorization");

    if (!authHeader.startsWith("Basic ")) {
        LOG_DEBUG(TAG, "Invalid auth type");
        return false;
    }

    String encoded = authHeader.substring(6);
    String decoded = decodeBase64(encoded);

    String expectedAuth = String(HTTP_AUTH_USERNAME) + ":" + String(HTTP_AUTH_PASSWORD);

    if (decoded == expectedAuth) {
        LOG_DEBUG(TAG, "Auth successful");
        return true;
    }

    LOG_WARN(TAG, "Auth failed from %s", request->client()->remoteIP().toString().c_str());
    return false;
}

bool AuthMiddleware::checkRateLimit(AsyncWebServerRequest* request) {
    if (rateLimit_ == 0) {
        return true;  // Rate limiting disabled
    }

    cleanupRateLimits();

    IPAddress ip = request->client()->remoteIP();
    RateLimitEntry* entry = getRateLimitEntry(ip);

    if (!entry) {
        LOG_WARN(TAG, "Rate limit entries full");
        return true;  // Allow if we can't track
    }

    uint32_t now = millis();
    uint32_t windowMs = 60000;  // 1 minute

    // Reset window if expired
    if (now - entry->windowStart > windowMs) {
        entry->windowStart = now;
        entry->requests = 0;
    }

    entry->requests++;

    if (entry->requests > rateLimit_) {
        LOG_WARN(TAG, "Rate limit exceeded for %s", ip.toString().c_str());
        return false;
    }

    return true;
}

void AuthMiddleware::sendUnauthorized(AsyncWebServerRequest* request) {
    AsyncWebServerResponse* response = request->beginResponse(401, "text/plain", "Unauthorized");
    response->addHeader("WWW-Authenticate", "Basic realm=\"ESP32-CAM\"");
    request->send(response);
}

ArRequestFilterFunction AuthMiddleware::getAuthFilter() {
    return [this](AsyncWebServerRequest* request) {
        if (!checkRateLimit(request)) {
            request->send(429, "text/plain", "Too Many Requests");
            return false;
        }
        if (!authenticate(request)) {
            sendUnauthorized(request);
            return false;
        }
        return true;
    };
}

RateLimitEntry* AuthMiddleware::getRateLimitEntry(const IPAddress& ip) {
    // Find existing entry
    for (size_t i = 0; i < rateEntryCount_; i++) {
        if (rateEntries_[i].ip == ip) {
            return &rateEntries_[i];
        }
    }

    // Create new entry if space available
    if (rateEntryCount_ < MAX_RATE_ENTRIES) {
        RateLimitEntry* entry = &rateEntries_[rateEntryCount_++];
        entry->ip = ip;
        entry->requests = 0;
        entry->windowStart = millis();
        return entry;
    }

    return nullptr;
}

void AuthMiddleware::cleanupRateLimits() {
    uint32_t now = millis();
    uint32_t windowMs = 60000;

    size_t writeIdx = 0;
    for (size_t i = 0; i < rateEntryCount_; i++) {
        if (now - rateEntries_[i].windowStart < windowMs * 2) {
            if (writeIdx != i) {
                rateEntries_[writeIdx] = rateEntries_[i];
            }
            writeIdx++;
        }
    }
    rateEntryCount_ = writeIdx;
}
