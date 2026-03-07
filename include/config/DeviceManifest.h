// include/config/DeviceManifest.h
// Unified device capability manifest
//
// Provides a single source of truth for all device capabilities,
// merging protocol-level caps (Version::Caps) with hardware caps (HandlerCap).

#pragma once

#include <cstdint>
#include <cstddef>
#include "config/Version.h"
#include "config/FeatureFlags.h"
#include "core/LoopRates.h"

namespace mara {

// Forward declarations
struct ServiceContext;

/// Unified capability bitmask combining all capability systems
namespace DeviceCap {
    // Protocol capabilities (from Version::Caps, bits 0-7)
    constexpr uint32_t BINARY_PROTOCOL   = 0x00000001;
    constexpr uint32_t INTENT_BUFFERING  = 0x00000002;
    constexpr uint32_t STATE_SPACE_CTRL  = 0x00000004;
    constexpr uint32_t OBSERVERS         = 0x00000008;

    // Transport capabilities (bits 8-11)
    constexpr uint32_t UART              = 0x00000100;
    constexpr uint32_t WIFI              = 0x00000200;
    constexpr uint32_t BLE               = 0x00000400;
    constexpr uint32_t MQTT              = 0x00000800;

    // Motor capabilities (bits 12-15)
    constexpr uint32_t DC_MOTOR          = 0x00001000;
    constexpr uint32_t SERVO             = 0x00002000;
    constexpr uint32_t STEPPER           = 0x00004000;
    constexpr uint32_t MOTION_CTRL       = 0x00008000;

    // Sensor capabilities (bits 16-19)
    constexpr uint32_t ENCODER           = 0x00010000;
    constexpr uint32_t IMU               = 0x00020000;
    constexpr uint32_t LIDAR             = 0x00040000;
    constexpr uint32_t ULTRASONIC        = 0x00080000;

    // Control capabilities (bits 20-23)
    constexpr uint32_t SIGNAL_BUS        = 0x00100000;
    constexpr uint32_t CONTROL_KERNEL    = 0x00200000;
    constexpr uint32_t OBSERVER          = 0x00400000;
    constexpr uint32_t PID_CONTROLLER    = 0x00800000;

    // System capabilities (bits 24-27)
    constexpr uint32_t TELEMETRY         = 0x01000000;
    constexpr uint32_t SAFETY            = 0x02000000;
    constexpr uint32_t AUDIO             = 0x04000000;
    constexpr uint32_t OTA               = 0x08000000;

    // Hardware I/O capabilities (bits 28-31)
    constexpr uint32_t GPIO              = 0x10000000;
    constexpr uint32_t PWM               = 0x20000000;
}

/// Device manifest containing all capability and configuration info
struct DeviceManifest {
    // Identification
    const char* firmware_version = Version::FIRMWARE;
    const char* board = Version::BOARD;
    const char* name = Version::NAME;
    uint8_t protocol_version = Version::PROTOCOL;
    uint8_t schema_version = Version::SCHEMA_VERSION;

    // Unified capabilities
    uint32_t caps = 0;

    // Active component counts
    uint8_t transport_count = 0;
    uint8_t sensor_count = 0;
    uint8_t actuator_count = 0;
    uint8_t handler_count = 0;
    uint8_t module_count = 0;

    // Loop rates (Hz)
    uint16_t control_hz = 0;
    uint16_t telemetry_hz = 0;
    uint16_t safety_hz = 0;

    // Active component names (null-terminated arrays)
    static constexpr size_t MAX_NAMES = 8;
    const char* transports[MAX_NAMES] = {nullptr};
    const char* sensors[MAX_NAMES] = {nullptr};
    const char* actuators[MAX_NAMES] = {nullptr};
};

/// Build device capability mask from compile-time flags
inline uint32_t buildDeviceCaps() {
    uint32_t caps = 0;

    // Protocol capabilities (using constexpr, evaluated at compile time)
    if constexpr ((Version::CAPABILITIES & Version::Caps::BINARY_PROTOCOL) != 0) {
        caps |= DeviceCap::BINARY_PROTOCOL;
    }
    if constexpr ((Version::CAPABILITIES & Version::Caps::INTENT_BUFFERING) != 0) {
        caps |= DeviceCap::INTENT_BUFFERING;
    }
    if constexpr ((Version::CAPABILITIES & Version::Caps::STATE_SPACE_CTRL) != 0) {
        caps |= DeviceCap::STATE_SPACE_CTRL;
    }
    if constexpr ((Version::CAPABILITIES & Version::Caps::OBSERVERS) != 0) {
        caps |= DeviceCap::OBSERVERS;
    }

    // Transport capabilities
#if HAS_UART_TRANSPORT
    caps |= DeviceCap::UART;
#endif
#if HAS_WIFI
    caps |= DeviceCap::WIFI;
#endif
#if HAS_BLE
    caps |= DeviceCap::BLE;
#endif
#if HAS_MQTT_TRANSPORT
    caps |= DeviceCap::MQTT;
#endif

    // Motor capabilities
#if HAS_DC_MOTOR
    caps |= DeviceCap::DC_MOTOR;
#endif
#if HAS_SERVO
    caps |= DeviceCap::SERVO;
#endif
#if HAS_STEPPER
    caps |= DeviceCap::STEPPER;
#endif
#if HAS_MOTION_CONTROLLER
    caps |= DeviceCap::MOTION_CTRL;
#endif

    // Sensor capabilities
#if HAS_ENCODER
    caps |= DeviceCap::ENCODER;
#endif
#if HAS_IMU
    caps |= DeviceCap::IMU;
#endif
#if HAS_LIDAR
    caps |= DeviceCap::LIDAR;
#endif
#if HAS_ULTRASONIC
    caps |= DeviceCap::ULTRASONIC;
#endif

    // Control capabilities
#if HAS_SIGNAL_BUS
    caps |= DeviceCap::SIGNAL_BUS;
#endif
#if HAS_CONTROL_KERNEL
    caps |= DeviceCap::CONTROL_KERNEL;
#endif
#if HAS_OBSERVER
    caps |= DeviceCap::OBSERVER;
#endif

    // System capabilities
#if HAS_TELEMETRY
    caps |= DeviceCap::TELEMETRY;
#endif
#if HAS_SAFETY_MANAGER
    caps |= DeviceCap::SAFETY;
#endif
#if HAS_AUDIO
    caps |= DeviceCap::AUDIO;
#endif

    // Hardware I/O capabilities
#if HAS_GPIO_MANAGER
    caps |= DeviceCap::GPIO;
#endif
#if HAS_PWM_MANAGER
    caps |= DeviceCap::PWM;
#endif

    return caps;
}

/// Build complete device manifest from ServiceContext
DeviceManifest buildManifest(const ServiceContext& ctx);

/// Convert capability bit to name (for JSON output)
const char* capBitToName(uint32_t bit);

} // namespace mara
