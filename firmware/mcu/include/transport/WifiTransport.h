// include/transport/WifiTransport.h
// WiFi TCP transport using HAL interfaces
#pragma once

#include "config/FeatureFlags.h"

#if HAS_WIFI

#include <vector>
#include "core/ITransport.h"
#include "core/Protocol.h"
#include "core/Debug.h"
#include "hal/ITcpServer.h"

/// WiFi TCP transport using HAL interfaces.
/// Platform-agnostic: works with any ITcpServer/ITcpClient implementation.
class WifiTransport : public ITransport {
public:
    /// @param server TCP server (caller retains ownership, transport does NOT delete)
    explicit WifiTransport(hal::ITcpServer* server)
        : server_(server) {}

    ~WifiTransport() {
        if (client_) {
            client_->stop();
            delete client_;
            client_ = nullptr;
        }
    }

    void begin() override {
        if (!server_) return;

        server_->begin();
        rxBuffer_.clear();
        rxBuffer_.reserve(256);

        DBG_PRINTF("[WifiTransport] listening on port %u\n", server_->getPort());
    }

    void loop() override {
        if (!server_) return;

        // Accept / monitor client
        if (!client_ || !client_->connected()) {
            // If we previously had a client and it disconnected, clean up
            if (client_) {
                DBG_PRINTLN("[WifiTransport] client disconnected");
                client_->stop();
                delete client_;
                client_ = nullptr;
            }

            // Check for new client
            client_ = server_->accept();
            if (client_) {
                char addrBuf[24];
                client_->getRemoteAddr(addrBuf, sizeof(addrBuf));
                DBG_PRINTF("[WifiTransport] client connected from %s:%u\n",
                           addrBuf, client_->getRemotePort());
            }
            return;
        }

        // Read bytes from client
        while (client_->available() > 0) {
            int b = client_->read();
            if (b >= 0) {
                rxBuffer_.push_back(static_cast<uint8_t>(b));
            }
        }

        // Frame extraction
        if (handler_) {
            Protocol::extractFrames(
                rxBuffer_,
                [this](const uint8_t* frame, size_t len) {
                    handler_(frame, len);
                }
            );
        }
    }

    bool sendBytes(const uint8_t* data, size_t len) override {
        if (!client_ || !client_->connected()) {
            return false;
        }
        size_t written = client_->write(data, len);
        return written == len;
    }

private:
    hal::ITcpServer*      server_ = nullptr;
    hal::ITcpClient*      client_ = nullptr;
    std::vector<uint8_t>  rxBuffer_;
};

#else // !HAS_WIFI

#include "core/ITransport.h"
#include "hal/ITcpServer.h"

// Stub when WiFi is disabled
class WifiTransport : public ITransport {
public:
    explicit WifiTransport(hal::ITcpServer*) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_WIFI
