// include/managers/EncoderManager.h
#pragma once

#include "config/FeatureFlags.h"

#if HAS_ENCODER

#include "hal/IGpio.h"
#include <cstdint>

// Forward declaration for auto-signals
class SignalBus;

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

    // Detach encoder
    void detach(uint8_t id);

    // -------------------------------------------------------------------------
    // Auto-Signals Support
    // -------------------------------------------------------------------------

    /// Enable auto-signal publishing to SignalBus.
    /// Defines signals for encoder count and velocity for each attached encoder.
    /// @param bus SignalBus instance to publish to
    /// @param rate_hz Desired publish rate
    void enableAutoSignals(SignalBus* bus, uint16_t rate_hz = 100);

    /// Disable auto-signal publishing
    void disableAutoSignals();

    /// Check if auto-signals are enabled
    bool autoSignalsEnabled() const { return signals_ != nullptr; }

    /// Publish current encoder readings to SignalBus.
    /// Should be called periodically (e.g., in main loop or control task).
    void publishToSignals(uint32_t now_ms);

    /// Set ticks per radian for velocity calculation (per encoder)
    void setTicksPerRad(uint8_t id, float ticksPerRad);

private:
    hal::IGpio* hal_ = nullptr;
    Encoder encoders_[MAX_ENCODERS];

    // Auto-signals state
    SignalBus* signals_ = nullptr;
    uint16_t signalRateHz_ = 100;
    uint32_t lastPublishMs_ = 0;
    bool signalsDefined_[MAX_ENCODERS] = {false};
    int32_t lastCount_[MAX_ENCODERS] = {0};
    uint32_t lastCountMs_[MAX_ENCODERS] = {0};
    float ticksPerRad_[MAX_ENCODERS] = {1.0f, 1.0f};
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
    void detach(uint8_t) {}
    int32_t getCount(uint8_t) const { return 0; }
    void reset(uint8_t) {}
    void handleA(uint8_t) {}
    void handleB(uint8_t) {}
    bool isAttached(uint8_t) const { return false; }
    void enableAutoSignals(void*, uint16_t = 100) {}
    void disableAutoSignals() {}
    bool autoSignalsEnabled() const { return false; }
    void publishToSignals(uint32_t) {}
    void setTicksPerRad(uint8_t, float) {}
};

inline EncoderManager* getGlobalEncoderManager() { return nullptr; }

#endif // HAS_ENCODER
