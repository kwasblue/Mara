// include/hal/linux/LinuxTransportFactory.h
// Linux transport factory implementation
//
// Creates Linux-specific transports (UART via termios, TCP sockets, etc.)
#pragma once

#include "../ITransportFactory.h"
#include <cstdint>

namespace hal {

/// Linux transport factory
///
/// Creates transport instances for Linux:
/// - UART via termios (/dev/ttyUSB*, /dev/ttyACM*, /dev/serial*)
/// - TCP client sockets
///
/// WiFi, BLE, and MQTT transports return nullptr (not supported in HAL,
/// use Python-side implementations if needed).
class LinuxTransportFactory : public ITransportFactory {
public:
    LinuxTransportFactory() = default;
    ~LinuxTransportFactory() = default;

    /// Create UART transport
    /// @param config UART configuration (port path in device field)
    /// @return Pointer to transport, or nullptr on failure
    void* createUart(const UartTransportConfig& config) override;

    /// Create WiFi transport (not supported on Linux HAL)
    /// @return Always nullptr
    void* createWifi(const WifiTransportConfig& config) override {
        (void)config;
        return nullptr;
    }

    /// Create BLE transport (not supported on Linux HAL)
    /// @return Always nullptr
    void* createBle(const BleTransportConfig& config) override {
        (void)config;
        return nullptr;
    }

    /// Create MQTT transport (not supported on Linux HAL)
    /// @return Always nullptr
    void* createMqtt(const MqttTransportConfig& config) override {
        (void)config;
        return nullptr;
    }

    /// Create CAN transport (not supported yet)
    /// @return Always nullptr
    void* createCan(const CanTransportConfig& config) override {
        (void)config;
        return nullptr;
    }

    /// Create TCP client transport
    /// @param host Hostname or IP address
    /// @param port Port number
    /// @return Pointer to transport, or nullptr on failure
    void* createTcpClient(const char* host, uint16_t port);
};

} // namespace hal
