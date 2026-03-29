// include/hal/ITransportFactory.h
// Abstract factory interface for transport creation.
// Allows platform-specific transport instantiation without coupling to concrete types.
#pragma once

#include <cstdint>

namespace hal {

/// Transport creation parameters
struct UartTransportConfig {
    void* serial = nullptr;      // HardwareSerial* on Arduino, void* for portability
    uint32_t baudRate = 115200;
};

struct WifiTransportConfig {
    uint16_t tcpPort = 3333;
};

struct BleTransportConfig {
    const char* deviceName = "ESP32-SPP";
};

struct MqttTransportConfig {
    const char* broker = nullptr;
    uint16_t port = 1883;
    const char* robotId = "node0";
    const char* username = nullptr;
    const char* password = nullptr;
};

struct CanTransportConfig {
    uint8_t nodeId = 0;
    uint32_t baudRate = 500000;
};

/// Abstract factory for creating transport instances.
/// Platform implementations provide concrete factories that create
/// platform-specific transports.
///
/// Return types are void* to avoid header coupling. Callers should cast
/// to the appropriate transport type (UartTransport*, WifiTransport*, etc.)
///
/// Usage:
///   ITransportFactory* factory = hal.transportFactory;
///   auto* uart = static_cast<UartTransport*>(factory->createUart(uartConfig));
///   auto* wifi = static_cast<WifiTransport*>(factory->createWifi(wifiConfig));
///
/// Memory ownership:
///   - Factory creates transports with `new`
///   - Caller is responsible for deleting transports
class ITransportFactory {
public:
    virtual ~ITransportFactory() = default;

    /// Create UART transport
    /// @param config UART configuration
    /// @return New UartTransport instance (as void*), or nullptr if not supported
    virtual void* createUart(const UartTransportConfig& config) = 0;

    /// Create WiFi TCP transport
    /// @param config WiFi configuration
    /// @return New WifiTransport instance (as void*), or nullptr if not supported
    virtual void* createWifi(const WifiTransportConfig& config) = 0;

    /// Create BLE transport
    /// @param config BLE configuration
    /// @return New BleTransport instance (as void*), or nullptr if not supported
    virtual void* createBle(const BleTransportConfig& config) = 0;

    /// Create MQTT transport
    /// @param config MQTT configuration
    /// @return New MqttTransport instance (as void*), or nullptr if not supported
    virtual void* createMqtt(const MqttTransportConfig& config) = 0;

    /// Create CAN transport
    /// @param config CAN configuration
    /// @return New CanTransport instance (as void*), or nullptr if not supported
    virtual void* createCan(const CanTransportConfig& config) = 0;
};

} // namespace hal
