// src/command/decoders/ObserverDecoders.cpp
// Implementation of observer command decoders

#include "command/decoders/ObserverDecoders.h"
#include "command/decoders/ControlDecoders.h"  // For extractUint16Array

namespace mara {
namespace cmd {

ObserverConfigResult decodeObserverConfig(JsonVariantConst payload) {
    ObserverConfigResult result;

    // Basic configuration
    result.slot = payload["slot"] | 0;
    result.rate_hz = payload["rate_hz"] | 200;

    // Observer dimensions
    result.config.num_states = payload["num_states"] | 2;
    result.config.num_inputs = payload["num_inputs"] | 1;
    result.config.num_outputs = payload["num_outputs"] | 1;

    // Input signal IDs (control commands u)
    JsonArrayConst input_ids = payload["input_ids"].as<JsonArrayConst>();
    if (input_ids) {
        extractUint16Array(input_ids, result.config.input_ids,
                          ObserverConfig::MAX_INPUTS);
    }

    // Output signal IDs (measurements y)
    JsonArrayConst output_ids = payload["output_ids"].as<JsonArrayConst>();
    if (output_ids) {
        extractUint16Array(output_ids, result.config.output_ids,
                          ObserverConfig::MAX_OUTPUTS);
    }

    // Estimate signal IDs (where to write x̂)
    JsonArrayConst estimate_ids = payload["estimate_ids"].as<JsonArrayConst>();
    if (estimate_ids) {
        extractUint16Array(estimate_ids, result.config.estimate_ids,
                          ObserverConfig::MAX_STATES);
    }

    result.valid = true;
    return result;
}

} // namespace cmd
} // namespace mara
