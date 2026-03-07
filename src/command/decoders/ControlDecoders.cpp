// src/command/decoders/ControlDecoders.cpp
// Implementation of control kernel command decoders

#include "command/decoders/ControlDecoders.h"
#include <cstring>
#include <algorithm>

namespace mara {
namespace cmd {

// =============================================================================
// Array Extraction Helpers
// =============================================================================

size_t extractUint16Array(JsonArrayConst arr, uint16_t* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;

    size_t count = std::min(arr.size(), maxLen);
    for (size_t i = 0; i < count; i++) {
        out[i] = arr[i].as<uint16_t>();
    }
    return count;
}

size_t extractFloatArray(JsonArrayConst arr, float* out, size_t maxLen) {
    if (!arr || !out || maxLen == 0) return 0;

    size_t count = std::min(arr.size(), maxLen);
    for (size_t i = 0; i < count; i++) {
        out[i] = arr[i].as<float>();
    }
    return count;
}

// =============================================================================
// Slot Configuration Decoder
// =============================================================================

SlotConfigResult decodeSlotConfig(JsonVariantConst payload) {
    SlotConfigResult result;

    // Basic slot configuration
    result.config.slot = payload["slot"] | 0;
    result.config.rate_hz = payload["rate_hz"] | 100;
    result.config.require_armed = payload["require_armed"] | true;
    result.config.require_active = payload["require_active"] | true;

    // Controller type
    result.controllerType = payload["controller_type"] | "PID";

    if (strcmp(result.controllerType, "STATE_SPACE") == 0 ||
        strcmp(result.controllerType, "SS") == 0) {
        // State-space configuration
        result.config.ss_io.num_states = payload["num_states"] | 2;
        result.config.ss_io.num_inputs = payload["num_inputs"] | 1;

        // Extract state signal IDs
        JsonArrayConst state_ids = payload["state_ids"].as<JsonArrayConst>();
        if (state_ids) {
            extractUint16Array(state_ids, result.config.ss_io.state_ids,
                              StateSpaceIO::MAX_STATES);
        }

        // Extract reference signal IDs
        JsonArrayConst ref_ids = payload["ref_ids"].as<JsonArrayConst>();
        if (ref_ids) {
            extractUint16Array(ref_ids, result.config.ss_io.ref_ids,
                              StateSpaceIO::MAX_STATES);
        }

        // Extract output signal IDs
        JsonArrayConst out_ids = payload["output_ids"].as<JsonArrayConst>();
        if (out_ids) {
            extractUint16Array(out_ids, result.config.ss_io.output_ids,
                              StateSpaceIO::MAX_INPUTS);
        }
    } else {
        // PID configuration
        result.config.io.ref_id = payload["ref_id"] | 0;
        result.config.io.meas_id = payload["meas_id"] | 0;
        result.config.io.out_id = payload["out_id"] | 0;
    }

    result.valid = true;
    return result;
}

// =============================================================================
// Signal Definition Decoder
// =============================================================================

SignalDefResult decodeSignalDef(JsonVariantConst payload) {
    SignalDefResult result;

    // Check required fields
    if (payload["id"].isNull() || payload["name"].isNull() || payload["kind"].isNull()) {
        result.error = "missing_fields";
        return result;
    }

    result.id = payload["id"].as<uint16_t>();

    // Copy name safely
    const char* name = payload["name"].as<const char*>();
    if (name) {
        strncpy(result.name, name, SignalBus::NAME_MAX_LEN);
        result.name[SignalBus::NAME_MAX_LEN] = '\0';
    }

    // Parse signal kind (support both "signal_kind" and "kind" keys)
    const char* kindStr = payload["signal_kind"] | payload["kind"] | "REF";
    result.kind = signalKindFromString(kindStr);

    // Initial value
    result.initial = payload["initial"] | 0.0f;

    result.valid = true;
    return result;
}

} // namespace cmd
} // namespace mara
