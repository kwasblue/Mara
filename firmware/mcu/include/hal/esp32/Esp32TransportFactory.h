// include/hal/esp32/Esp32TransportFactory.h
// ESP32 transport factory implementation
#pragma once

#include "../ITransportFactory.h"
#include "config/FeatureFlags.h"

namespace hal {

// Forward declaration
class ICan;

/// ESP32 transport factory implementation.
/// Creates ESP32-specific transport instances.
class Esp32TransportFactory : public ITransportFactory {
public:
    Esp32TransportFactory() = default;

    /// Set CAN HAL for CAN transport creation
    void setCanHal(ICan* can) { canHal_ = can; }

    void* createUart(const UartTransportConfig& config) override;
    void* createWifi(const WifiTransportConfig& config) override;
    void* createBle(const BleTransportConfig& config) override;
    void* createMqtt(const MqttTransportConfig& config) override;
    void* createCan(const CanTransportConfig& config) override;

private:
    ICan* canHal_ = nullptr;
};

} // namespace hal
