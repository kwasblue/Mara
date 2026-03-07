// include/core/ControlKernel.h
// Multi-slot controller manager for real-time control

#pragma once

#include <cstdint>
#include <vector>
#include <memory>
#include <cstring>
#include <functional>
#include "control/SignalBus.h"

// Forward declaration
class IController;

// -----------------------------------------------------------------------------
// Control Watchdog - monitors controller execution for stuck/slow controllers
// -----------------------------------------------------------------------------
class ControlWatchdog {
public:
    using TimeoutCallback = std::function<void(uint8_t slot, uint32_t elapsed_ms)>;

    ControlWatchdog() = default;

    // Configure timeout threshold (0 = disabled)
    void setTimeout(uint32_t timeout_ms) { timeout_ms_ = timeout_ms; }
    uint32_t getTimeout() const { return timeout_ms_; }

    // Set callback for timeout events
    void onTimeout(TimeoutCallback cb) { callback_ = std::move(cb); }

    // Call before slot computation begins
    void beginSlot(uint8_t slot, uint32_t now_ms);

    // Call after slot computation ends
    void endSlot(uint8_t slot, uint32_t now_ms);

    // Periodic check - call from main loop to detect stuck slots
    void check(uint32_t now_ms);

    // Get max execution time observed for a slot
    uint32_t getMaxExecTime(uint8_t slot) const;

    // Reset statistics
    void resetStats();

private:
    static constexpr size_t MAX_SLOTS = 8;

    struct SlotTiming {
        uint32_t start_ms = 0;
        bool in_progress = false;
        uint32_t max_exec_ms = 0;
        uint32_t last_complete_ms = 0;
    };

    SlotTiming slots_[MAX_SLOTS];
    uint32_t timeout_ms_ = 0;  // 0 = disabled
    TimeoutCallback callback_;
};

// -----------------------------------------------------------------------------
// State-Space Configuration
// -----------------------------------------------------------------------------
struct StateSpaceIO {
    static constexpr size_t MAX_STATES = 6;
    static constexpr size_t MAX_INPUTS = 2;
    
    uint8_t num_states = 0;
    uint8_t num_inputs = 1;
    
    uint16_t state_ids[MAX_STATES] = {0};   // Measurement signal IDs
    uint16_t ref_ids[MAX_STATES] = {0};     // Reference signal IDs (for tracking)
    uint16_t output_ids[MAX_INPUTS] = {0};  // Output signal IDs
};

// -----------------------------------------------------------------------------
// Slot I/O configuration (for single-input controllers like PID)
// -----------------------------------------------------------------------------
struct SlotIO {
    uint16_t ref_id  = 0;   // Reference/setpoint signal ID
    uint16_t meas_id = 0;   // Measurement signal ID
    uint16_t out_id  = 0;   // Output signal ID
};

// Slot configuration
struct SlotConfig {
    uint8_t slot = 0;
    uint16_t rate_hz = 100;
    bool enabled = false;
    SlotIO io;                  // For PID
    StateSpaceIO ss_io;         // For State-Space
    bool require_armed = true;
    bool require_active = true;
};

// Slot runtime status
struct SlotStatus {
    bool ok = false;
    uint32_t run_count = 0;
    uint32_t last_run_ms = 0;
    const char* last_error = nullptr;
};

// -----------------------------------------------------------------------------
// IController Interface
// -----------------------------------------------------------------------------
class IController {
public:
    virtual ~IController() = default;
    
    // Compute output from reference and measurement
    virtual float compute(float ref, float meas, float dt_s) = 0;
    
    // Multi-state compute (for state-space). Default falls back to single compute.
    virtual void computeMulti(
        const float* states, const float* refs, uint8_t num_states,
        float* outputs, uint8_t num_outputs,
        float dt_s, SignalBus& signals, const StateSpaceIO& io
    ) {
        // Default: use single compute for backwards compatibility
        if (num_states > 0 && num_outputs > 0) {
            outputs[0] = compute(refs[0], states[0], dt_s);
        }
    }
    
    // Reset internal state (integrators, etc)
    virtual void reset() = 0;
    
    // Set a parameter by name
    virtual bool setParam(const char* key, float value) = 0;
    
    // Get a parameter by name
    virtual bool getParam(const char* key, float& value) const = 0;
    
    // Set array parameter (for gain matrices)
    virtual bool setParamArray(const char* key, const float* values, size_t len) {
        (void)key; (void)values; (void)len;
        return false;
    }
    
    // Check if this is a multi-state controller
    virtual bool isMultiState() const { return false; }
};

// -----------------------------------------------------------------------------
// PID Controller Implementation
// -----------------------------------------------------------------------------
class PidController : public IController {
public:
    PidController(float kp = 1.0f, float ki = 0.0f, float kd = 0.0f);
    
    float compute(float ref, float meas, float dt_s) override;
    void reset() override;
    bool setParam(const char* key, float value) override;
    bool getParam(const char* key, float& value) const override;

    
    // Direct setters
    void setGains(float kp, float ki, float kd);
    void setOutputLimits(float min_out, float max_out);
    void setIntegralLimits(float min_i, float max_i);

private:
    float kp_ = 1.0f;
    float ki_ = 0.0f;
    float kd_ = 0.0f;
    
    float out_min_ = -1.0f;
    float out_max_ = 1.0f;
    float i_min_ = -1.0f;
    float i_max_ = 1.0f;
    
    float integral_ = 0.0f;
    float prev_error_ = 0.0f;
    bool first_run_ = true;
};

// -----------------------------------------------------------------------------
// State-Space Controller Implementation
// -----------------------------------------------------------------------------
// Implements: u = -K * x + Kr * r  (state feedback with reference feedforward)
// Or:         u = -K * (x - xr)    (error-based feedback)
//
// With optional integral action for steady-state tracking
// -----------------------------------------------------------------------------
class StateSpaceController : public IController {
public:
    static constexpr size_t MAX_STATES = StateSpaceIO::MAX_STATES;
    static constexpr size_t MAX_INPUTS = StateSpaceIO::MAX_INPUTS;
    
    StateSpaceController();
    
    // Single compute not used - returns 0
    float compute(float ref, float meas, float dt_s) override { 
        (void)ref; (void)meas; (void)dt_s;
        return 0.0f; 
    }
    
    // Multi-state compute
    void computeMulti(
        const float* states, const float* refs, uint8_t num_states,
        float* outputs, uint8_t num_outputs,
        float dt_s, SignalBus& signals, const StateSpaceIO& io
    ) override;
    
    void reset() override;
    bool setParam(const char* key, float value) override;
    bool getParam(const char* key, float& value) const override;
    bool setParamArray(const char* key, const float* values, size_t len) override;
    bool isMultiState() const override { return true; }
    
    // Configuration
    void setDimensions(uint8_t num_states, uint8_t num_inputs);
    void setGainK(const float* K, size_t len);          // State feedback gain
    void setGainKr(const float* Kr, size_t len);        // Reference feedforward gain
    void setGainKi(const float* Ki, size_t len);        // Integral gain
    void setOutputLimits(uint8_t output_idx, float min_val, float max_val);
    void setIntegralLimits(uint8_t output_idx, float min_val, float max_val);
    void setFeedbackMode(bool error_based);             // true = u = -K*(x-xr), false = u = -Kx + Kr*r

private:
    uint8_t num_states_ = 0;
    uint8_t num_inputs_ = 1;
    
    // Gain matrix K (num_inputs x num_states), stored row-major
    // u[j] = -sum(K[j*num_states + i] * x[i])
    float K_[MAX_INPUTS * MAX_STATES] = {0};
    
    // Reference feedforward Kr (num_inputs x num_states)
    // u[j] += sum(Kr[j*num_states + i] * r[i])
    float Kr_[MAX_INPUTS * MAX_STATES] = {0};
    
    // Integral gains Ki (num_inputs) - integrates first state error only
    float Ki_[MAX_INPUTS] = {0};
    
    // Integrator state
    float integrator_[MAX_INPUTS] = {0};
    float integrator_min_[MAX_INPUTS] = {-1.0f, -1.0f};
    float integrator_max_[MAX_INPUTS] = {1.0f, 1.0f};
    
    // Output limits
    float u_min_[MAX_INPUTS] = {-1.0f, -1.0f};
    float u_max_[MAX_INPUTS] = {1.0f, 1.0f};
    
    // Feedback mode: true = error-based, false = state + feedforward
    bool error_based_ = true;
    
    // Helper
    float clamp(float val, float min_val, float max_val) const {
        return val < min_val ? min_val : (val > max_val ? max_val : val);
    }
};

// -----------------------------------------------------------------------------
// ControlKernel
// -----------------------------------------------------------------------------
class ControlKernel {
public:
    static constexpr size_t MAX_SLOTS = 8;

    ControlKernel() = default;
    ~ControlKernel() = default;

    // Access to watchdog for configuration
    ControlWatchdog& watchdog() { return watchdog_; }
    const ControlWatchdog& watchdog() const { return watchdog_; }

    // Configure a slot with controller type ("PID" or "STATE_SPACE")
    bool configureSlot(const SlotConfig& cfg, const char* type);
    
    // Enable/disable a slot
    bool enableSlot(uint8_t slot, bool enable);
    
    // Reset a slot's controller state
    bool resetSlot(uint8_t slot);
    
    // Set a parameter on a slot's controller
    bool setParam(uint8_t slot, const char* key, float value);

    // Get a parameter from a slot's controller
    bool getParam(uint8_t slot, const char* key, float& value) const;

    // Set array parameter (for gain matrices)
    bool setParamArray(uint8_t slot, const char* key, const float* values, size_t len);
    
    // Get slot configuration
    SlotConfig getConfig(uint8_t slot) const;
    
    // Get slot status
    SlotStatus getStatus(uint8_t slot) const;
    
    // Step all enabled controllers
    void step(uint32_t now_ms, float dt_s, SignalBus& signals, bool is_armed, bool is_active);
    
    // Reset all slots
    void resetAll();
    
    // Disable all slots
    void disableAll();

private:
    struct Slot {
        SlotConfig cfg;
        SlotStatus status;
        std::unique_ptr<IController> ctrl;
        uint32_t last_step_ms = 0;
    };

    std::vector<Slot> slots_;
    ControlWatchdog watchdog_;

    Slot* getSlot_(uint8_t slot);
    const Slot* getSlot_(uint8_t slot) const;
    void ensureSlot_(uint8_t slot);
};