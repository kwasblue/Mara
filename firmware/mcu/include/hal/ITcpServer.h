// include/hal/ITcpServer.h
// Abstract TCP server/client interfaces for WiFi transport.
// Abstracts ESP32 WiFiServer/WiFiClient for platform portability.
#pragma once

#include <cstddef>
#include <cstdint>

namespace hal {

/// Abstract TCP client interface.
/// Wraps platform-specific TCP client (WiFiClient on ESP32).
class ITcpClient {
public:
    virtual ~ITcpClient() = default;

    /// Check if client is connected
    virtual bool connected() = 0;

    /// Number of bytes available to read
    virtual int available() = 0;

    /// Read a single byte. Returns -1 if no data available.
    virtual int read() = 0;

    /// Write bytes to the client
    /// @return Number of bytes written
    virtual size_t write(const uint8_t* data, size_t len) = 0;

    /// Close the connection
    virtual void stop() = 0;

    /// Get remote address as string for logging
    /// @param buf Buffer to store address string
    /// @param bufSize Size of buffer
    virtual void getRemoteAddr(char* buf, size_t bufSize) = 0;

    /// Get remote port for logging
    virtual uint16_t getRemotePort() = 0;
};

/// Abstract TCP server interface.
/// Wraps platform-specific TCP server (WiFiServer on ESP32).
class ITcpServer {
public:
    virtual ~ITcpServer() = default;

    /// Start listening on the configured port
    virtual void begin() = 0;

    /// Check for and accept new client connections
    /// @return New client if available, nullptr otherwise
    /// @note Caller takes ownership of returned client
    virtual ITcpClient* accept() = 0;

    /// Get the port the server is listening on
    virtual uint16_t getPort() const = 0;
};

/// Factory for creating TCP server instances
/// This allows the WiFi HAL to create servers without coupling to concrete types
class ITcpServerFactory {
public:
    virtual ~ITcpServerFactory() = default;

    /// Create a TCP server on the specified port
    /// @param port Port to listen on
    /// @return New server instance (caller owns)
    virtual ITcpServer* createServer(uint16_t port) = 0;
};

} // namespace hal
