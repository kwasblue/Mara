// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from VERSION in platform_schema.py

#pragma once
#include <cstdint>

namespace Version {
    constexpr const char* FIRMWARE = "1.0.0";
    constexpr uint8_t PROTOCOL = 1;
    constexpr uint8_t SCHEMA_VERSION = 1;
    constexpr const char* BOARD = "esp32";
    constexpr const char* NAME = "robot";

    // Device capabilities bitfield
    constexpr uint32_t CAPABILITIES = 0x000F;

    // Individual capability flags
    namespace Caps {
        constexpr uint32_t BINARY_PROTOCOL = 0x0001;
        constexpr uint32_t INTENT_BUFFERING = 0x0002;
        constexpr uint32_t STATE_SPACE_CTRL = 0x0004;
        constexpr uint32_t OBSERVERS = 0x0008;
    }
}
