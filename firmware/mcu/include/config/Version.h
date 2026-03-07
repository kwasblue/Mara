// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from VERSION in platform_schema.py

#pragma once
#include <cstdint>

namespace Version {
    constexpr const char* FIRMWARE = "1.0.0";
    constexpr uint8_t PROTOCOL = 1;
    constexpr uint8_t SCHEMA_VERSION = 1;  // Schema evolution version
    constexpr const char* BOARD = "esp32";
    constexpr const char* NAME = "robot";

    // Capability bitfield for feature advertisement
    namespace Caps {
        constexpr uint32_t BINARY_PROTOCOL   = 0x0001;  // Binary frame protocol support
        constexpr uint32_t INTENT_BUFFERING  = 0x0002;  // Command-to-actuator intent buffering
        constexpr uint32_t STATE_SPACE_CTRL  = 0x0004;  // State-space controller support
        constexpr uint32_t OBSERVERS         = 0x0008;  // Luenberger observer support
    }

    // Combined capabilities mask
    constexpr uint32_t CAPABILITIES =
        Caps::BINARY_PROTOCOL |
        Caps::INTENT_BUFFERING |
        Caps::STATE_SPACE_CTRL |
        Caps::OBSERVERS;
}
