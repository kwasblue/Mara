// include/command/CommandDecoders.h
// Decoders for typed commands from JSON payloads
//
// Usage:
//   auto result = decodeSetVelocity(payload);
//   if (result.valid) {
//       executeSetVelocity(result.cmd, ctx);
//   } else {
//       ctx.sendError(cmdName, result.error);
//   }

#pragma once

#include <ArduinoJson.h>
#include <cmath>
#include "command/TypedCommands.h"

namespace mara {
namespace cmd {

// =============================================================================
// Motion Command Decoders
// =============================================================================

inline DecodeResult<SetVelocityCmd> decodeSetVelocity(JsonVariantConst payload) {
    SetVelocityCmd cmd;

    if (payload["vx"].isNull() && payload["omega"].isNull()) {
        return DecodeResult<SetVelocityCmd>::fail("missing_vx_or_omega");
    }

    cmd.vx = payload["vx"] | 0.0f;
    cmd.omega = payload["omega"] | 0.0f;

    if (!cmd.isValid()) {
        return DecodeResult<SetVelocityCmd>::fail("invalid_velocity");
    }

    return DecodeResult<SetVelocityCmd>::ok(cmd);
}

// =============================================================================
// Signal Command Decoders
// =============================================================================

inline DecodeResult<SetSignalCmd> decodeSetSignal(JsonVariantConst payload) {
    SetSignalCmd cmd;

    if (payload["id"].isNull()) {
        return DecodeResult<SetSignalCmd>::fail("missing_id");
    }
    if (payload["value"].isNull()) {
        return DecodeResult<SetSignalCmd>::fail("missing_value");
    }

    cmd.id = payload["id"].as<uint16_t>();
    cmd.value = payload["value"].as<float>();

    if (!cmd.isValid()) {
        return DecodeResult<SetSignalCmd>::fail("invalid_value");
    }

    return DecodeResult<SetSignalCmd>::ok(cmd);
}

// =============================================================================
// Rate Command Decoders
// =============================================================================

inline DecodeResult<SetRateCmd> decodeSetRate(
    JsonVariantConst payload,
    uint16_t min_hz,
    uint16_t max_hz
) {
    SetRateCmd cmd;
    cmd.min_hz = min_hz;
    cmd.max_hz = max_hz;

    if (payload["hz"].isNull()) {
        return DecodeResult<SetRateCmd>::fail("missing_hz");
    }

    cmd.hz = payload["hz"].as<uint16_t>();
    return DecodeResult<SetRateCmd>::ok(cmd);
}

// =============================================================================
// GPIO Command Decoders
// =============================================================================

inline DecodeResult<GpioWriteCmd> decodeGpioWrite(JsonVariantConst payload) {
    GpioWriteCmd cmd;

    if (payload["pin"].isNull()) {
        return DecodeResult<GpioWriteCmd>::fail("missing_pin");
    }

    cmd.pin = payload["pin"].as<uint8_t>();
    cmd.value = payload["value"] | false;

    return DecodeResult<GpioWriteCmd>::ok(cmd);
}

inline DecodeResult<GpioReadCmd> decodeGpioRead(JsonVariantConst payload) {
    GpioReadCmd cmd;

    if (payload["pin"].isNull()) {
        return DecodeResult<GpioReadCmd>::fail("missing_pin");
    }

    cmd.pin = payload["pin"].as<uint8_t>();
    return DecodeResult<GpioReadCmd>::ok(cmd);
}

// =============================================================================
// Slot Command Decoders
// =============================================================================

inline DecodeResult<SlotEnableCmd> decodeSlotEnable(JsonVariantConst payload) {
    SlotEnableCmd cmd;

    if (payload["slot"].isNull()) {
        return DecodeResult<SlotEnableCmd>::fail("missing_slot");
    }

    cmd.slot = payload["slot"].as<uint8_t>();
    if (cmd.slot >= 8) {
        return DecodeResult<SlotEnableCmd>::fail("invalid_slot");
    }

    cmd.enable = payload["enable"] | false;
    return DecodeResult<SlotEnableCmd>::ok(cmd);
}

inline DecodeResult<SlotResetCmd> decodeSlotReset(JsonVariantConst payload) {
    SlotResetCmd cmd;

    if (payload["slot"].isNull()) {
        return DecodeResult<SlotResetCmd>::fail("missing_slot");
    }

    cmd.slot = payload["slot"].as<uint8_t>();
    if (cmd.slot >= 8) {
        return DecodeResult<SlotResetCmd>::fail("invalid_slot");
    }

    return DecodeResult<SlotResetCmd>::ok(cmd);
}

inline DecodeResult<SlotSetParamCmd> decodeSlotSetParam(JsonVariantConst payload) {
    SlotSetParamCmd cmd;

    if (payload["slot"].isNull()) {
        return DecodeResult<SlotSetParamCmd>::fail("missing_slot");
    }
    if (payload["key"].isNull()) {
        return DecodeResult<SlotSetParamCmd>::fail("missing_key");
    }
    if (payload["value"].isNull()) {
        return DecodeResult<SlotSetParamCmd>::fail("missing_value");
    }

    cmd.slot = payload["slot"].as<uint8_t>();
    if (cmd.slot >= 8) {
        return DecodeResult<SlotSetParamCmd>::fail("invalid_slot");
    }

    cmd.key = payload["key"].as<const char*>();
    cmd.value = payload["value"].as<float>();

    if (!cmd.isValid()) {
        return DecodeResult<SlotSetParamCmd>::fail("invalid_value");
    }

    return DecodeResult<SlotSetParamCmd>::ok(cmd);
}

// =============================================================================
// Shared Array Utilities
// =============================================================================

/// Extract uint16_t array from JSON (for signal IDs)
/// Returns number of elements extracted
inline size_t extractUint16Array(JsonArrayConst arr, uint16_t* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;
    size_t count = 0;
    for (size_t i = 0; i < arr.size() && i < maxLen; i++) {
        out[i] = arr[i].as<uint16_t>();
        count++;
    }
    return count;
}

/// Extract float array from JSON (for matrices, gains)
/// Returns number of elements extracted
inline size_t extractFloatArray(JsonArrayConst arr, float* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;
    size_t count = 0;
    for (size_t i = 0; i < arr.size() && i < maxLen; i++) {
        out[i] = arr[i].as<float>();
        count++;
    }
    return count;
}

/// Validate array size matches expected
/// Sets error message and returns false if mismatch
inline bool validateArraySize(size_t actual, size_t expected, const char* name, const char** error) {
    if (actual != expected) {
        *error = name;  // Caller handles formatting
        return false;
    }
    return true;
}

} // namespace cmd
} // namespace mara
