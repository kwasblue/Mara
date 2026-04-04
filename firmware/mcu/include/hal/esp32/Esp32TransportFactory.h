// include/hal/esp32/Esp32TransportFactory.h
// ESP32 transport factory implementation
#pragma once

#include "../ITransportFactory.h"
#include "../IByteStream.h"
#include "../IBleByteStream.h"
#include "../ITcpServer.h"
#include "config/FeatureFlags.h"

namespace hal {

// Forward declaration
class ICan;

/// ESP32 transport factory implementation.
/// Creates ESP32-specific transport instances.
///
/// The factory owns the HAL implementations (streams, servers) that it creates.
/// These are stored internally and live as long as the factory does.
/// The transports themselves are owned by the caller.
class Esp32TransportFactory : public ITransportFactory {
public:
    Esp32TransportFactory() = default;
    ~Esp32TransportFactory();

    /// Set CAN HAL for CAN transport creation
    void setCanHal(ICan* can) { canHal_ = can; }

    void* createUart(const UartTransportConfig& config) override;
    void* createWifi(const WifiTransportConfig& config) override;
    void* createBle(const BleTransportConfig& config) override;
    void* createMqtt(const MqttTransportConfig& config) override;
    void* createCan(const CanTransportConfig& config) override;

private:
    ICan* canHal_ = nullptr;

    // HAL implementations owned by factory
    // Only one of each type is created, reused across transports
    IByteStream* uartStream_ = nullptr;
    ITcpServer* tcpServer_ = nullptr;
    IBleByteStream* bleStream_ = nullptr;
};

} // namespace hal
