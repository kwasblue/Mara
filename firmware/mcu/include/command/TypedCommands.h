// include/command/TypedCommands.h
// Typed command structures for unified JSON/binary handling
//
// Both JSON and binary commands decode into these typed structs.
// Executors operate on typed structs, not raw JSON or binary data.
// This eliminates validation duplication and enables property-based testing.

#pragma once

#include <cstdint>
#include <cmath>
#include "core/Result.h"
#include "config/CommandDefs.h"

namespace mara {
namespace cmd {

// =============================================================================
// Motion Commands
// =============================================================================

struct SetVelocityCmd {
    float vx = 0.0f;
    float omega = 0.0f;

    /// Validate the command values
    bool isValid() const {
        return !std::isnan(vx) && !std::isinf(vx) &&
               !std::isnan(omega) && !std::isinf(omega);
    }
};

struct StopCmd {
    // No parameters
};

// =============================================================================
// Signal Commands
// =============================================================================

struct SetSignalCmd {
    uint16_t id = 0;
    float value = 0.0f;

    bool isValid() const {
        return !std::isnan(value) && !std::isinf(value);
    }
};

// =============================================================================
// Safety Commands
// =============================================================================

struct ArmCmd {
    // No parameters - just the command
};

struct DisarmCmd {
    // No parameters
};

struct EstopCmd {
    // No parameters
};

struct ClearEstopCmd {
    // No parameters
};

// =============================================================================
// GPIO Commands
// =============================================================================

struct GpioWriteCmd {
    uint8_t pin = 0;
    bool value = false;
};

struct GpioReadCmd {
    uint8_t pin = 0;
};

// =============================================================================
// Rate Commands
// =============================================================================

struct SetRateCmd {
    uint16_t hz = 0;
    uint16_t min_hz = 1;
    uint16_t max_hz = 1000;

    bool isValid() const {
        return hz >= min_hz && hz <= max_hz;
    }

    /// Clamp to valid range, returns true if was already in range
    bool clamp() {
        if (hz < min_hz) { hz = min_hz; return false; }
        if (hz > max_hz) { hz = max_hz; return false; }
        return true;
    }
};

// =============================================================================
// Controller Slot Commands
// =============================================================================

struct SlotConfigCmd {
    uint8_t slot = 0;
    const char* type = nullptr;  // "PID" or "SS"
    uint16_t rate_hz = 100;
    uint16_t ref_id = 0;
    uint16_t meas_id = 0;
    uint16_t out_id = 0;
    bool require_armed = true;
    bool require_active = true;

    bool isValid() const {
        return slot < 8 && type != nullptr && rate_hz > 0;
    }
};

struct SlotEnableCmd {
    uint8_t slot = 0;
    bool enable = false;
};

struct SlotResetCmd {
    uint8_t slot = 0;
};

struct SlotSetParamCmd {
    uint8_t slot = 0;
    const char* key = nullptr;
    float value = 0.0f;

    bool isValid() const {
        return slot < 8 && key != nullptr &&
               !std::isnan(value) && !std::isinf(value);
    }
};

// =============================================================================
// Decoder Results
// =============================================================================

/// Result of decoding a command from JSON or binary
template<typename T>
struct DecodeResult {
    bool valid = false;
    T cmd;
    const char* error = nullptr;

    static DecodeResult ok(const T& c) {
        DecodeResult r;
        r.valid = true;
        r.cmd = c;
        return r;
    }

    static DecodeResult fail(const char* err) {
        DecodeResult r;
        r.valid = false;
        r.error = err;
        return r;
    }
};

} // namespace cmd
} // namespace mara
