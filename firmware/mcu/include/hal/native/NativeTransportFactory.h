// include/hal/native/NativeTransportFactory.h
// Native transport factory stub for testing
#pragma once

#include "../ITransportFactory.h"

namespace hal {

/// Native transport factory stub for testing.
/// Returns nullptr for all transports since native builds
/// don't have actual transport hardware.
///
/// In tests, use mock transports injected directly instead
/// of going through this factory.
class NativeTransportFactory : public ITransportFactory {
public:
    NativeTransportFactory() = default;

    void* createUart(const UartTransportConfig& config) override {
        (void)config;
        return nullptr;  // No UART in native builds
    }

    void* createWifi(const WifiTransportConfig& config) override {
        (void)config;
        return nullptr;  // No WiFi in native builds
    }

    void* createBle(const BleTransportConfig& config) override {
        (void)config;
        return nullptr;  // No BLE in native builds
    }

    void* createMqtt(const MqttTransportConfig& config) override {
        (void)config;
        return nullptr;  // No MQTT in native builds
    }

    void* createCan(const CanTransportConfig& config) override {
        (void)config;
        return nullptr;  // No CAN in native builds
    }
};

} // namespace hal
