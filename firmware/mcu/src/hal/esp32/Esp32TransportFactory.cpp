// src/hal/esp32/Esp32TransportFactory.cpp
// ESP32 transport factory implementation

#include "config/PlatformConfig.h"

#if PLATFORM_ESP32

#include "hal/esp32/Esp32TransportFactory.h"
#include "config/FeatureFlags.h"
#include "transport/UartTransport.h"
#include "transport/WifiTransport.h"
#include "transport/BleTransport.h"
#include "transport/MqttTransport.h"
#include "transport/CanTransport.h"
#include <Arduino.h>

namespace hal {

void* Esp32TransportFactory::createUart(const UartTransportConfig& config) {
    if (!config.serial) {
        return nullptr;
    }
    auto* serial = static_cast<HardwareSerial*>(config.serial);
    return new UartTransport(*serial, config.baudRate);
}

void* Esp32TransportFactory::createWifi(const WifiTransportConfig& config) {
#if HAS_WIFI
    return new WifiTransport(config.tcpPort);
#else
    (void)config;
    return nullptr;
#endif
}

void* Esp32TransportFactory::createBle(const BleTransportConfig& config) {
#if HAS_BLE
    return new BleTransport(config.deviceName);
#else
    (void)config;
    return nullptr;
#endif
}

void* Esp32TransportFactory::createMqtt(const MqttTransportConfig& config) {
#if HAS_MQTT_TRANSPORT && HAS_WIFI
    if (!config.broker) {
        return nullptr;
    }
    return new MqttTransport(
        config.broker,
        config.port,
        config.robotId,
        config.username,
        config.password
    );
#else
    (void)config;
    return nullptr;
#endif
}

void* Esp32TransportFactory::createCan(const CanTransportConfig& config) {
#if HAS_CAN
    auto* transport = new CanTransport();
    if (canHal_) {
        transport->setHal(canHal_);
    }
    transport->setNodeId(config.nodeId);
    transport->setBaudRate(config.baudRate);
    return transport;
#else
    (void)config;
    return nullptr;
#endif
}

} // namespace hal

#endif // PLATFORM_ESP32
