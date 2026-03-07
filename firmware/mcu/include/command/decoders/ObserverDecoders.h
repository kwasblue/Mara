// include/command/decoders/ObserverDecoders.h
// Decoders for observer commands

#pragma once

#include <ArduinoJson.h>
#include "control/Observer.h"

namespace mara {
namespace cmd {

// =============================================================================
// Observer Configuration Decoder
// =============================================================================

struct ObserverConfigResult {
    bool valid = false;
    const char* error = nullptr;
    uint8_t slot = 0;
    uint16_t rate_hz = 200;
    ObserverConfig config;
};

/// Decode CMD_OBSERVER_CONFIG payload
ObserverConfigResult decodeObserverConfig(JsonVariantConst payload);

} // namespace cmd
} // namespace mara
