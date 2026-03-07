// include/core/Observer.h
// State observer for control systems

#pragma once

#include "config/FeatureFlags.h"

#if HAS_OBSERVER

#include <cstdint>
#include <cstring>
#include <algorithm>

class SignalBus;  // Forward declaration

// -----------------------------------------------------------------------------
// Observer Configuration
// -----------------------------------------------------------------------------
struct ObserverConfig {
    static constexpr size_t MAX_STATES = 6;
    static constexpr size_t MAX_INPUTS = 2;
    static constexpr size_t MAX_OUTPUTS = 4;
    
    uint8_t num_states = 2;
    uint8_t num_inputs = 1;
    uint8_t num_outputs = 1;
    
    // Signal routing
    uint16_t input_ids[MAX_INPUTS] = {0};      // Control input signal IDs (u)
    uint16_t output_ids[MAX_OUTPUTS] = {0};    // Measurement signal IDs (y)
    uint16_t estimate_ids[MAX_STATES] = {0};   // Where to write estimated states (x̂)
};

// -----------------------------------------------------------------------------
// Luenberger Observer
// -----------------------------------------------------------------------------
// Implements: x̂[k+1] = A·x̂[k] + B·u[k] + L·(y[k] - C·x̂[k])
// -----------------------------------------------------------------------------
class LuenbergerObserver {
public:
    static constexpr size_t MAX_STATES = ObserverConfig::MAX_STATES;
    static constexpr size_t MAX_INPUTS = ObserverConfig::MAX_INPUTS;
    static constexpr size_t MAX_OUTPUTS = ObserverConfig::MAX_OUTPUTS;
    
    LuenbergerObserver() { reset(); }
    
    // Configure dimensions
    void configure(uint8_t num_states, uint8_t num_inputs, uint8_t num_outputs);
    
    // Run one observer step
    void update(const float* u, const float* y, float dt, float* x_hat_out);
    
    // Reset state estimate
    void reset();
    
    // Initialize state estimate from values
    void initState(const float* x0);
    
    // Set/get individual state
    void setState(uint8_t idx, float value);
    float getState(uint8_t idx) const;
    const float* getStates() const { return x_hat_; }
    
    bool isInitialized() const { return initialized_; }
    
    // Matrix setters
    bool setA(const float* A, size_t len);
    bool setB(const float* B, size_t len);
    bool setC(const float* C, size_t len);
    bool setL(const float* L, size_t len);
    
    // Set individual element: "A01", "B10", "C00", "L10"
    bool setParam(const char* key, float value);
    bool setParamArray(const char* key, const float* values, size_t len);
    
    // Getters for debugging
    uint8_t numStates() const { return num_states_; }
    uint8_t numInputs() const { return num_inputs_; }
    uint8_t numOutputs() const { return num_outputs_; }

private:
    uint8_t num_states_ = 2;
    uint8_t num_inputs_ = 1;
    uint8_t num_outputs_ = 1;
    bool initialized_ = false;
    
    // State estimate
    float x_hat_[MAX_STATES] = {0};
    
    // System matrices (continuous-time, stored with MAX dimensions for indexing)
    float A_[MAX_STATES * MAX_STATES] = {0};   // State transition (n×n)
    float B_[MAX_STATES * MAX_INPUTS] = {0};   // Input (n×m)
    float C_[MAX_OUTPUTS * MAX_STATES] = {0};  // Output (p×n)
    float L_[MAX_STATES * MAX_OUTPUTS] = {0};  // Observer gain (n×p)
    
    // Helper for clamping
    static float clamp(float v, float lo, float hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }
};

// -----------------------------------------------------------------------------
// ObserverManager - Manages multiple observers
// -----------------------------------------------------------------------------
class ObserverManager {
public:
    static constexpr size_t MAX_OBSERVERS = 4;
    static constexpr size_t MAX_SLOTS = 4;

    
    struct Slot {
        bool configured = false;
        bool enabled = false;
        ObserverConfig config;
        LuenbergerObserver observer;
        uint32_t last_update_ms = 0;
        uint16_t rate_hz = 200;
        uint32_t update_count = 0;
    };
    
    // Configure an observer slot
    bool configure(uint8_t slot, const ObserverConfig& config, uint16_t rate_hz = 200);
    
    // Enable/disable
    bool enable(uint8_t slot, bool en);
    
    // Reset
    bool reset(uint8_t slot);
    
    // Set parameters
    bool setParam(uint8_t slot, const char* key, float value);
    bool setParamArray(uint8_t slot, const char* key, const float* values, size_t len);
    
    // Step all enabled observers
    void step(uint32_t now_ms, float dt_s, SignalBus& signals);
    
    // Access
    LuenbergerObserver* getObserver(uint8_t slot);
    const Slot& getSlot(uint8_t slot) const;
    
    // Reset all
    void resetAll();
    void disableAll();

private:
    Slot slots_[MAX_OBSERVERS];
};

#else // !HAS_OBSERVER

#include <cstdint>
#include <cstddef>

class SignalBus;

// Stub ObserverConfig
struct ObserverConfig {
    static constexpr size_t MAX_STATES = 6;
    static constexpr size_t MAX_INPUTS = 2;
    static constexpr size_t MAX_OUTPUTS = 4;
    uint8_t num_states = 2;
    uint8_t num_inputs = 1;
    uint8_t num_outputs = 1;
    uint16_t input_ids[MAX_INPUTS] = {0};
    uint16_t output_ids[MAX_OUTPUTS] = {0};
    uint16_t estimate_ids[MAX_STATES] = {0};
};

// Stub LuenbergerObserver
class LuenbergerObserver {
public:
    static constexpr size_t MAX_STATES = 6;
    static constexpr size_t MAX_INPUTS = 2;
    static constexpr size_t MAX_OUTPUTS = 4;

    LuenbergerObserver() {}
    void configure(uint8_t, uint8_t, uint8_t) {}
    void update(const float*, const float*, float, float*) {}
    void reset() {}
    void initState(const float*) {}
    void setState(uint8_t, float) {}
    float getState(uint8_t) const { return 0.0f; }
    const float* getStates() const { return nullptr; }
    bool isInitialized() const { return false; }
    bool setA(const float*, size_t) { return false; }
    bool setB(const float*, size_t) { return false; }
    bool setC(const float*, size_t) { return false; }
    bool setL(const float*, size_t) { return false; }
    bool setParam(const char*, float) { return false; }
    bool setParamArray(const char*, const float*, size_t) { return false; }
    uint8_t numStates() const { return 0; }
    uint8_t numInputs() const { return 0; }
    uint8_t numOutputs() const { return 0; }
};

// Stub ObserverManager
class ObserverManager {
public:
    static constexpr size_t MAX_OBSERVERS = 4;
    static constexpr size_t MAX_SLOTS = 4;

    struct Slot {
        bool configured = false;
        bool enabled = false;
        ObserverConfig config;
        LuenbergerObserver observer;
        uint32_t last_update_ms = 0;
        uint16_t rate_hz = 200;
        uint32_t update_count = 0;
    };

    bool configure(uint8_t, const ObserverConfig&, uint16_t = 200) { return false; }
    bool enable(uint8_t, bool) { return false; }
    bool reset(uint8_t) { return false; }
    bool setParam(uint8_t, const char*, float) { return false; }
    bool setParamArray(uint8_t, const char*, const float*, size_t) { return false; }
    void step(uint32_t, float, SignalBus&) {}
    LuenbergerObserver* getObserver(uint8_t) { return nullptr; }
    const Slot& getSlot(uint8_t slot) const { return empty_; }
    void resetAll() {}
    void disableAll() {}

private:
    Slot empty_;
    Slot slots_[MAX_OBSERVERS];
};

#endif // HAS_OBSERVER