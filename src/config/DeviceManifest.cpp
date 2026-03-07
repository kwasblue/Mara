// src/config/DeviceManifest.cpp
// Unified device manifest implementation

#include "config/DeviceManifest.h"
#include "core/ServiceContext.h"
#include "command/HandlerRegistry.h"
#include "core/ModuleManager.h"
#include "sensor/SensorRegistry.h"
#include "sensor/ISensor.h"
#include "transport/TransportRegistry.h"  // Includes IRegisteredTransport
#include "motor/ActuatorRegistry.h"
#include "motor/IActuator.h"

namespace mara {

DeviceManifest buildManifest(const ServiceContext& ctx) {
    DeviceManifest m;

    // Compile-time capabilities
    m.caps = buildDeviceCaps();

    // Loop rates
    const auto& rates = getLoopRates();
    m.control_hz = rates.ctrl_hz;
    m.telemetry_hz = rates.telem_hz;
    m.safety_hz = rates.safety_hz;

    // Component counts from registries
    if (ctx.handlerRegistry) {
        m.handler_count = static_cast<uint8_t>(ctx.handlerRegistry->handlerCount());
    }
    if (ctx.moduleManager) {
        m.module_count = static_cast<uint8_t>(ctx.moduleManager->moduleCount());
    }
    if (ctx.sensorRegistry) {
        m.sensor_count = static_cast<uint8_t>(ctx.sensorRegistry->count());
        // Populate sensor names using iterators
        size_t idx = 0;
        for (auto* s : *ctx.sensorRegistry) {
            if (idx >= DeviceManifest::MAX_NAMES) break;
            if (s) m.sensors[idx++] = s->name();
        }
    }
    if (ctx.transportRegistry) {
        m.transport_count = static_cast<uint8_t>(ctx.transportRegistry->count());
        // Populate transport names using iterators
        size_t idx = 0;
        for (auto* t : *ctx.transportRegistry) {
            if (idx >= DeviceManifest::MAX_NAMES) break;
            if (t) m.transports[idx++] = t->name();
        }
    }
    if (ctx.actuatorRegistry) {
        m.actuator_count = static_cast<uint8_t>(ctx.actuatorRegistry->count());
        // Populate actuator names using iterators
        size_t idx = 0;
        for (auto* a : *ctx.actuatorRegistry) {
            if (idx >= DeviceManifest::MAX_NAMES) break;
            if (a) m.actuators[idx++] = a->name();
        }
    }

    return m;
}

const char* capBitToName(uint32_t bit) {
    switch (bit) {
        // Protocol
        case DeviceCap::BINARY_PROTOCOL:  return "binary_protocol";
        case DeviceCap::INTENT_BUFFERING: return "intent_buffering";
        case DeviceCap::STATE_SPACE_CTRL: return "state_space_ctrl";
        case DeviceCap::OBSERVERS:        return "observers";

        // Transport
        case DeviceCap::UART:             return "uart";
        case DeviceCap::WIFI:             return "wifi";
        case DeviceCap::BLE:              return "ble";
        case DeviceCap::MQTT:             return "mqtt";

        // Motor
        case DeviceCap::DC_MOTOR:         return "dc_motor";
        case DeviceCap::SERVO:            return "servo";
        case DeviceCap::STEPPER:          return "stepper";
        case DeviceCap::MOTION_CTRL:      return "motion_ctrl";

        // Sensor
        case DeviceCap::ENCODER:          return "encoder";
        case DeviceCap::IMU:              return "imu";
        case DeviceCap::LIDAR:            return "lidar";
        case DeviceCap::ULTRASONIC:       return "ultrasonic";

        // Control
        case DeviceCap::SIGNAL_BUS:       return "signal_bus";
        case DeviceCap::CONTROL_KERNEL:   return "control_kernel";
        case DeviceCap::OBSERVER:         return "observer";
        case DeviceCap::PID_CONTROLLER:   return "pid_controller";

        // System
        case DeviceCap::TELEMETRY:        return "telemetry";
        case DeviceCap::SAFETY:           return "safety";
        case DeviceCap::AUDIO:            return "audio";
        case DeviceCap::OTA:              return "ota";

        default:                          return "unknown";
    }
}

} // namespace mara
