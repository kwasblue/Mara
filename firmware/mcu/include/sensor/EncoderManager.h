// include/managers/EncoderManager.h
#pragma once

#include "config/FeatureFlags.h"

#if HAS_ENCODER

#include "hal/IGpio.h"
#include <cstdint>

// Simple quadrature encoder manager (A/B only, no index/Z yet).
// - Supports up to MAX_ENCODERS encoders
// - Uses ISR callbacks wired in EncoderManager.cpp
// - Count is signed: positive / negative based on direction
// - Now uses HAL GPIO for platform portability
class EncoderManager {
public:
    struct Encoder {
        volatile int32_t count      = 0;
        uint8_t          pinA       = 0;
        uint8_t          pinB       = 0;
        bool             initialized = false;
    };

    static constexpr uint8_t MAX_ENCODERS = 2;

    EncoderManager();

    /// Set the HAL GPIO driver (must be called before attach)
    void setHal(hal::IGpio* gpio) { hal_ = gpio; }

    // Attach an encoder to A/B pins and install ISR(s).
    // id must be < MAX_ENCODERS.
    void attach(uint8_t id, uint8_t pinA, uint8_t pinB);

    // Get current tick count (signed). Safe-ish snapshot.
    int32_t getCount(uint8_t id) const;

    // Reset tick count to 0.
    void reset(uint8_t id);

    // ISR helpers called from static ISRs:
    void handleA(uint8_t id);
    void handleB(uint8_t id);

    // Optional: simple presence check
    bool isAttached(uint8_t id) const {
        return (id < MAX_ENCODERS) && encoders_[id].initialized;
    }

private:
    hal::IGpio* hal_ = nullptr;
    Encoder encoders_[MAX_ENCODERS];
};

// Global pointer used by file-local ISRs to call into the manager.
EncoderManager* getGlobalEncoderManager();

#else // !HAS_ENCODER

#include <cstdint>

namespace hal { class IGpio; }

// Stub when encoder is disabled
class EncoderManager {
public:
    struct Encoder {
        volatile int32_t count = 0;
        uint8_t pinA = 0;
        uint8_t pinB = 0;
        bool initialized = false;
    };

    static constexpr uint8_t MAX_ENCODERS = 2;

    EncoderManager() = default;
    void setHal(hal::IGpio*) {}
    void attach(uint8_t, uint8_t, uint8_t) {}
    int32_t getCount(uint8_t) const { return 0; }
    void reset(uint8_t) {}
    void handleA(uint8_t) {}
    void handleB(uint8_t) {}
    bool isAttached(uint8_t) const { return false; }
};

inline EncoderManager* getGlobalEncoderManager() { return nullptr; }

#endif // HAS_ENCODER
