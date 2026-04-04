// include/hal/esp32/Esp32TcpServer.h
// ESP32 TCP server/client implementation wrapping WiFiServer/WiFiClient
#pragma once

#include "config/FeatureFlags.h"

#if HAS_WIFI

#include "../ITcpServer.h"
#include <WiFi.h>

namespace hal {

/// ESP32 TCP client implementation wrapping WiFiClient
class Esp32TcpClient : public ITcpClient {
public:
    Esp32TcpClient() = default;
    explicit Esp32TcpClient(WiFiClient client) : client_(client) {}

    bool connected() override {
        return client_.connected();
    }

    int available() override {
        return client_.available();
    }

    int read() override {
        return client_.read();
    }

    size_t write(const uint8_t* data, size_t len) override {
        return client_.write(data, len);
    }

    void stop() override {
        client_.stop();
    }

    void getRemoteAddr(char* buf, size_t bufSize) override {
        IPAddress ip = client_.remoteIP();
        snprintf(buf, bufSize, "%d.%d.%d.%d", ip[0], ip[1], ip[2], ip[3]);
    }

    uint16_t getRemotePort() override {
        return client_.remotePort();
    }

    /// Check if client is valid (has been assigned)
    bool isValid() const {
        return client_.connected();
    }

    /// Update underlying client (for accepting new connections)
    void setClient(WiFiClient client) {
        client_ = client;
    }

private:
    mutable WiFiClient client_;  // mutable for connected() const
};

/// ESP32 TCP server implementation wrapping WiFiServer
class Esp32TcpServer : public ITcpServer {
public:
    explicit Esp32TcpServer(uint16_t port)
        : server_(port), port_(port) {}

    void begin() override {
        server_.begin();
    }

    ITcpClient* accept() override {
        WiFiClient newClient = server_.available();
        if (newClient) {
            return new Esp32TcpClient(newClient);
        }
        return nullptr;
    }

    uint16_t getPort() const override {
        return port_;
    }

private:
    WiFiServer server_;
    uint16_t port_;
};

/// ESP32 TCP server factory implementation
class Esp32TcpServerFactory : public ITcpServerFactory {
public:
    ITcpServer* createServer(uint16_t port) override {
        return new Esp32TcpServer(port);
    }
};

} // namespace hal

#else // !HAS_WIFI

#include "../ITcpServer.h"

namespace hal {

// Stubs when WiFi is disabled
class Esp32TcpClient : public ITcpClient {
public:
    bool connected() override { return false; }
    int available() override { return 0; }
    int read() override { return -1; }
    size_t write(const uint8_t*, size_t) override { return 0; }
    void stop() override {}
    void getRemoteAddr(char* buf, size_t bufSize) override {
        if (bufSize > 0) buf[0] = '\0';
    }
    uint16_t getRemotePort() override { return 0; }
};

class Esp32TcpServer : public ITcpServer {
public:
    explicit Esp32TcpServer(uint16_t) {}
    void begin() override {}
    ITcpClient* accept() override { return nullptr; }
    uint16_t getPort() const override { return 0; }
};

class Esp32TcpServerFactory : public ITcpServerFactory {
public:
    ITcpServer* createServer(uint16_t) override { return nullptr; }
};

} // namespace hal

#endif // HAS_WIFI
