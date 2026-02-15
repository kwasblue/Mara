#pragma once

#include <Arduino.h>
#include <ESPAsyncWebServer.h>
#include "config/AuthSecrets.h"
#include "config/DefaultSettings.h"

// Rate limiter entry
struct RateLimitEntry {
    IPAddress ip;
    uint32_t requests;
    uint32_t windowStart;
};

class AuthMiddleware {
public:
    AuthMiddleware();

    // Configure auth settings
    void setEnabled(bool enabled);
    void setRateLimit(uint8_t requestsPerMinute);

    // Check if auth is enabled
    bool isEnabled() const { return authEnabled_; }

    // Authenticate a request (returns true if authorized)
    bool authenticate(AsyncWebServerRequest* request);

    // Check rate limit (returns true if allowed)
    bool checkRateLimit(AsyncWebServerRequest* request);

    // Send 401 response
    void sendUnauthorized(AsyncWebServerRequest* request);

    // Create a filter function for protected routes
    ArRequestFilterFunction getAuthFilter();

private:
    bool authEnabled_ = DEFAULT_AUTH_ENABLED;
    uint8_t rateLimit_ = DEFAULT_RATE_LIMIT;

    static constexpr size_t MAX_RATE_ENTRIES = 10;
    RateLimitEntry rateEntries_[MAX_RATE_ENTRIES];
    size_t rateEntryCount_ = 0;

    // Find or create rate limit entry for IP
    RateLimitEntry* getRateLimitEntry(const IPAddress& ip);

    // Clean up old entries
    void cleanupRateLimits();
};
