// include/command/decoders/ControlDecoders.h
// Decoders for control kernel commands (slots and signals)

#pragma once

#include <ArduinoJson.h>
#include "control/ControlKernel.h"
#include "control/SignalBus.h"

namespace mara {
namespace cmd {

// =============================================================================
// Slot Configuration Decoder
// =============================================================================

struct SlotConfigResult {
    bool valid = false;
    const char* error = nullptr;
    SlotConfig config;
    const char* controllerType = "PID";
};

/// Decode CMD_CTRL_SLOT_CONFIG payload
SlotConfigResult decodeSlotConfig(JsonVariantConst payload);

// =============================================================================
// Signal Definition Decoder
// =============================================================================

struct SignalDefResult {
    bool valid = false;
    const char* error = nullptr;
    uint16_t id = 0;
    char name[SignalBus::NAME_MAX_LEN + 1] = {0};
    SignalBus::Kind kind = SignalBus::Kind::REF;
    float initial = 0.0f;
};

/// Decode CMD_CTRL_SIGNAL_DEFINE payload
SignalDefResult decodeSignalDef(JsonVariantConst payload);

// =============================================================================
// Array Extraction Helpers
// =============================================================================

/// Extract uint16_t array from JSON (for signal IDs)
/// Returns number of elements extracted
size_t extractUint16Array(JsonArrayConst arr, uint16_t* out, size_t maxLen);

/// Extract float array from JSON (for matrices, gains)
/// Returns number of elements extracted
size_t extractFloatArray(JsonArrayConst arr, float* out, size_t maxLen);

} // namespace cmd
} // namespace mara
