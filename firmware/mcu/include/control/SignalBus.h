// include/core/SignalBus.h
// Signal routing system for control kernel
// Stores named signals with values and timestamps
//
// Thread Safety:
//   - Individual get/set operations are protected with spinlock
//   - Use snapshot() for thread-safe bulk reads (telemetry)
//   - all() returns raw reference - use only during setup or with external sync

#pragma once

#include "config/FeatureFlags.h"
#include "config/GeneratedLimits.h"

#if HAS_SIGNAL_BUS

#include <cstdint>
#include <vector>
#include <cstring>
#include <unordered_map>
#include "core/CriticalSection.h"
#include "core/RealTimeContract.h"

// -----------------------------------------------------------------------------
// Signal Namespace - Reserved ID ranges for auto-signals
// -----------------------------------------------------------------------------
// User-defined signals: 1-999
// Auto-signals (hardware managers): 1000-1999
// This prevents collisions between user-defined signals and auto-published
// hardware readings.

namespace SignalNamespace {
    // User-defined signals: 1-999
    static constexpr uint16_t USER_MIN = 1;
    static constexpr uint16_t USER_MAX = 999;

    // Auto-signals: 1000-1999
    static constexpr uint16_t AUTO_MIN = 1000;
    static constexpr uint16_t AUTO_MAX = 1999;

    // IMU: 1000-1019
    static constexpr uint16_t IMU_AX = 1000;
    static constexpr uint16_t IMU_AY = 1001;
    static constexpr uint16_t IMU_AZ = 1002;
    static constexpr uint16_t IMU_GX = 1003;
    static constexpr uint16_t IMU_GY = 1004;
    static constexpr uint16_t IMU_GZ = 1005;
    static constexpr uint16_t IMU_PITCH = 1006;
    static constexpr uint16_t IMU_ROLL = 1007;

    // Encoders: 1020-1039 (encoder_id offset: 1020 + encoder_id*2 for count, +1 for velocity)
    static constexpr uint16_t ENCODER_BASE = 1020;
    static constexpr uint16_t ENCODER_COUNT_OFFSET = 0;
    static constexpr uint16_t ENCODER_VEL_OFFSET = 1;

    // DC Motors: 1040-1059 (motor_id offset: 1040 + motor_id for PWM output)
    static constexpr uint16_t DC_MOTOR_BASE = 1040;

    // Servos: 1060-1079 (servo_id offset: 1060 + servo_id for angle)
    static constexpr uint16_t SERVO_BASE = 1060;

    // Ultrasonic: 1080-1099 (sensor_id offset: 1080 + sensor_id for distance)
    static constexpr uint16_t ULTRASONIC_BASE = 1080;

    // Check if an ID is in the auto-signal range
    inline bool isAutoSignal(uint16_t id) {
        return id >= AUTO_MIN && id <= AUTO_MAX;
    }

    // Check if an ID is in the user-defined range
    inline bool isUserSignal(uint16_t id) {
        return id >= USER_MIN && id <= USER_MAX;
    }
}

class SignalBus {
public:
    SignalBus() {
        mara::initSpinlock(lock_);
    }

    enum class Kind : uint8_t {
        REF  = 0,   // Reference/setpoint
        MEAS = 1,   // Measurement/feedback
        OUT  = 2,    // Control output
        EST = 3    // State estimate
    };

    // Rate limiting result
    enum class SetResult : uint8_t {
        OK = 0,                 // Value was set
        SIGNAL_NOT_FOUND = 1,   // Signal ID doesn't exist
        RATE_LIMITED_TIME = 2,  // Skipped due to min interval
        RATE_LIMITED_COUNT = 3  // Skipped due to max updates/sec
    };

    // Fixed-size name buffer to avoid dangling pointer issues with JSON strings
    static constexpr size_t NAME_MAX_LEN = 64;

    // Maximum number of signals that can be defined (configured in mara_build.yaml)
    static constexpr size_t MAX_SIGNALS = MARA_MAX_SIGNALS;

    struct SignalDef {
        uint16_t id = 0;
        char name[NAME_MAX_LEN + 1] = {0};  // Fixed buffer, null-terminated
        Kind kind = Kind::REF;
        float value = 0.0f;
        uint32_t ts_ms = 0;
        // Rate limiting state (per-signal)
        uint32_t last_set_ms = 0;
        uint16_t updates_this_sec = 0;
        uint32_t rate_window_start = 0;
        // Auto-signal protection: read_only prevents external set() calls
        bool read_only = false;
    };

    // Define a new user signal (returns false if ID already exists or is in auto-signal range)
    // User signals must be in range 1-999
    bool define(uint16_t id, const char* name, Kind kind, float initial = 0.0f);

    // Define an auto-signal (used by hardware managers, e.g., IMU, encoders)
    // Auto-signals are read-only and cannot be modified by external set() calls
    // Auto-signals must be in range 1000-1999
    bool defineAutoSignal(uint16_t id, const char* name, Kind kind, float initial = 0.0f);

    // Set auto-signal value (bypasses read_only check, for hardware managers only)
    RT_SAFE bool setAutoSignal(uint16_t id, float v, uint32_t now_ms = 0);

    // Check if signal exists
    bool exists(uint16_t id) const;
    
    // Set signal value with timestamp
    RT_SAFE bool set(uint16_t id, float v, uint32_t now_ms = 0);

    // Set with rate limiting (checks min interval and max updates/sec)
    SetResult setWithRateLimit(uint16_t id, float v, uint32_t now_ms);

    // Configure global rate limits (0 = disabled)
    void setGlobalRateLimit(uint32_t min_interval_ms, uint16_t max_updates_per_sec);

    // Get current rate limit config
    uint32_t getMinInterval() const { return global_min_interval_ms_; }
    uint16_t getMaxUpdatesPerSec() const { return global_max_updates_per_sec_; }

    // Get signal value
    RT_SAFE bool get(uint16_t id, float& out) const;
    
    // Get signal timestamp
    bool getTimestamp(uint16_t id, uint32_t& out) const;
    
    //remove
    bool remove(uint16_t id);
    
    // Get signal by ID (returns nullptr if not found)
    const SignalDef* find(uint16_t id) const;
    
    // Access all signals - NOT THREAD SAFE
    // Use only during setup or with external synchronization
    // For telemetry, use snapshot() instead
    const std::vector<SignalDef>& all() const { return signals_; }

    // Number of defined signals
    size_t count() const { return signals_.size(); }

    // Clear all signals - NOT THREAD SAFE, use during setup only
    void clear() { signals_.clear(); idToIndex_.clear(); aliases_.clear(); }

    // -------------------------------------------------------------------------
    // Thread-safe snapshot for telemetry
    // -------------------------------------------------------------------------

    /// Lightweight signal value for snapshots (no name storage)
    struct SignalSnapshot {
        uint16_t id = 0;
        float value = 0.0f;
        uint32_t ts_ms = 0;
        Kind kind = Kind::REF;
    };

    /// Take thread-safe snapshot of all signal values
    /// Returns number of signals copied
    size_t snapshot(SignalSnapshot* out, size_t max_count) const;

    // -------------------------------------------------------------------------
    // Signal Aliasing - reference signals by name
    // -------------------------------------------------------------------------

    // Create an alias for a signal ID (returns false if alias already exists)
    bool createAlias(uint16_t id, const char* alias);

    // Remove an alias
    bool removeAlias(const char* alias);

    // Get signal value by name (checks signal names first, then aliases)
    bool getByName(const char* name, float& out) const;

    // Set signal value by name
    bool setByName(const char* name, float v, uint32_t now_ms = 0);

    // Resolve name to ID (returns 0 if not found)
    uint16_t resolveId(const char* name) const;

    // -------------------------------------------------------------------------
    // Signal Trace Subscription - stream selected signals via telemetry
    // -------------------------------------------------------------------------

    /// Set signals to trace (max 16). Pass empty array to disable.
    /// rate_hz: Update rate for trace telemetry (default 10Hz, max 50Hz)
    void setTraceSignals(const uint16_t* ids, size_t count, uint16_t rate_hz = 10);

    /// Get current trace configuration
    size_t getTracedSignals(uint16_t* outIds, size_t maxCount) const;
    uint16_t getTraceRateHz() const { return trace_rate_hz_; }

    /// Get snapshot of traced signals (for telemetry)
    /// Returns number of signals written
    size_t getTracedSnapshot(SignalSnapshot* out, size_t maxCount) const;

    /// Check if tracing is enabled
    bool isTraceEnabled() const { return trace_count_ > 0; }

private:
    std::vector<SignalDef> signals_;
    std::unordered_map<uint16_t, size_t> idToIndex_;  // O(1) lookup cache
    int indexOf_(uint16_t id) const;

    // Global rate limits
    uint32_t global_min_interval_ms_ = 0;     // 0 = no limit
    uint16_t global_max_updates_per_sec_ = 0; // 0 = no limit

    // Alias storage
    struct Alias {
        char name[NAME_MAX_LEN + 1] = {0};
        uint16_t id = 0;
    };
    std::vector<Alias> aliases_;

    // Thread safety (spinlock)
    mutable mara::SpinlockType lock_ = MCU_SPINLOCK_INIT;

    // Signal trace subscription
    static constexpr size_t MAX_TRACE_SIGNALS = 16;
    uint16_t trace_ids_[MAX_TRACE_SIGNALS] = {0};
    size_t trace_count_ = 0;
    uint16_t trace_rate_hz_ = 10;  // Default 10Hz
};

// -----------------------------------------------------------------------------
// SignalRef - Cached reference for high-rate access
// -----------------------------------------------------------------------------
class SignalRef {
public:
    SignalRef(SignalBus& bus, const char* name)
        : bus_(bus), name_(name), id_(0), resolved_(false) {}

    // Resolve the name to an ID (call once at setup)
    bool resolve() {
        id_ = bus_.resolveId(name_);
        resolved_ = (id_ != 0);
        return resolved_;
    }

    // Check if resolved
    bool isResolved() const { return resolved_; }

    // Get value (fast path when resolved)
    bool get(float& out) const {
        if (!resolved_) return false;
        return bus_.get(id_, out);
    }

    // Set value (fast path when resolved)
    bool set(float v, uint32_t now_ms = 0) {
        if (!resolved_) return false;
        return bus_.set(id_, v, now_ms);
    }

    // Get the cached ID
    uint16_t id() const { return id_; }

private:
    SignalBus& bus_;
    const char* name_;
    uint16_t id_;
    bool resolved_;
};

// Helper to convert Kind to string
inline const char* signalKindToString(SignalBus::Kind k) {
    switch (k) {
        case SignalBus::Kind::REF:  return "REF";
        case SignalBus::Kind::MEAS: return "MEAS";
        case SignalBus::Kind::OUT:  return "OUT";
        case SignalBus::Kind::EST:  return "EST";
        
        default: return "UNK";
    }
}

// Helper to parse Kind from string
inline SignalBus::Kind signalKindFromString(const char* s) {
    if (!s) return SignalBus::Kind::REF;
    if (strcmp(s, "REF") == 0)  return SignalBus::Kind::REF;
    if (strcmp(s, "MEAS") == 0) return SignalBus::Kind::MEAS;
    if (strcmp(s, "OUT") == 0)  return SignalBus::Kind::OUT;
    if (strcmp(s, "EST") == 0)  return SignalBus::Kind::EST;
    return SignalBus::Kind::REF;
}

#else // !HAS_SIGNAL_BUS

#include <cstdint>
#include <vector>

// Stub when SignalBus is disabled
class SignalBus {
public:
    enum class Kind : uint8_t { REF = 0, MEAS = 1, OUT = 2, EST = 3 };
    enum class SetResult : uint8_t { OK = 0, SIGNAL_NOT_FOUND = 1 };
    static constexpr size_t NAME_MAX_LEN = 64;

    struct SignalDef {
        uint16_t id = 0;
        char name[NAME_MAX_LEN + 1] = {0};
        Kind kind = Kind::REF;
        float value = 0.0f;
        uint32_t ts_ms = 0;
    };

    struct SignalSnapshot {
        uint16_t id = 0;
        float value = 0.0f;
        uint32_t ts_ms = 0;
        Kind kind = Kind::REF;
    };

    bool define(uint16_t, const char*, Kind, float = 0.0f) { return false; }
    bool defineAutoSignal(uint16_t, const char*, Kind, float = 0.0f) { return false; }
    bool setAutoSignal(uint16_t, float, uint32_t = 0) { return false; }
    bool exists(uint16_t) const { return false; }
    bool set(uint16_t, float, uint32_t = 0) { return false; }
    SetResult setWithRateLimit(uint16_t, float, uint32_t) { return SetResult::SIGNAL_NOT_FOUND; }
    void setGlobalRateLimit(uint32_t, uint16_t) {}
    uint32_t getMinInterval() const { return 0; }
    uint16_t getMaxUpdatesPerSec() const { return 0; }
    bool get(uint16_t, float&) const { return false; }
    bool getWithTs(uint16_t, float&, uint32_t&) const { return false; }
    bool getTimestamp(uint16_t, uint32_t&) const { return false; }
    const SignalDef* find(uint16_t) const { return nullptr; }
    const std::vector<SignalDef>& all() const { return empty_; }
    size_t count() const { return 0; }
    size_t snapshot(SignalSnapshot*, size_t) const { return 0; }
    const SignalDef* getByIndex(size_t) const { return nullptr; }
    bool remove(uint16_t) { return false; }
    bool deleteSignal(uint16_t) { return false; }
    void clear() {}
    bool createAlias(uint16_t, const char*) { return false; }
    bool removeAlias(const char*) { return false; }
    bool getByName(const char*, float&) const { return false; }
    bool setByName(const char*, float, uint32_t = 0) { return false; }
    uint16_t resolveId(const char*) const { return 0; }
    void setTraceSignals(const uint16_t*, size_t, uint16_t = 10) {}
    size_t getTracedSignals(uint16_t*, size_t) const { return 0; }
    uint16_t getTraceRateHz() const { return 0; }
    size_t getTracedSnapshot(SignalSnapshot*, size_t) const { return 0; }
    bool isTraceEnabled() const { return false; }

private:
    std::vector<SignalDef> empty_;
};

class SignalRef {
public:
    SignalRef(SignalBus&, const char*) {}
    bool resolve() { return false; }
    bool isResolved() const { return false; }
    bool get(float&) const { return false; }
    bool set(float, uint32_t = 0) { return false; }
    uint16_t id() const { return 0; }
};

inline const char* signalKindToString(SignalBus::Kind) { return "UNK"; }
inline SignalBus::Kind signalKindFromString(const char*) { return SignalBus::Kind::REF; }

#endif // HAS_SIGNAL_BUS