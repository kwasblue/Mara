// src/core/ControlKernel.cpp
// Multi-slot controller manager implementation

#include "control/ControlKernel.h"
#include <cstring>
#include <algorithm>

// -----------------------------------------------------------------------------
// ControlKernel Implementation
// -----------------------------------------------------------------------------

ControlKernel::Slot* ControlKernel::getSlot_(uint8_t slot) {
    for (auto& s : slots_) {
        if (s.cfg.slot == slot) return &s;
    }
    return nullptr;
}

const ControlKernel::Slot* ControlKernel::getSlot_(uint8_t slot) const {
    for (const auto& s : slots_) {
        if (s.cfg.slot == slot) return &s;
    }
    return nullptr;
}

void ControlKernel::ensureSlot_(uint8_t slot) {
    if (getSlot_(slot)) return;
    if (slots_.size() >= MAX_SLOTS) return;
    
    Slot s;
    s.cfg.slot = slot;
    slots_.push_back(std::move(s));
}

bool ControlKernel::configureSlot(const SlotConfig& cfg, const char* type) {
    if (cfg.slot >= MAX_SLOTS) return false;
    
    ensureSlot_(cfg.slot);
    Slot* s = getSlot_(cfg.slot);
    if (!s) return false;
    
    s->cfg = cfg;
    s->cfg.enabled = false;  // Start disabled
    s->status = SlotStatus{};
    
    // Create controller based on type
    if (strcmp(type, "PID") == 0) {
        s->ctrl = std::make_unique<PidController>();
    } else if (strcmp(type, "STATE_SPACE") == 0 || strcmp(type, "SS") == 0) {
        auto ss = std::make_unique<StateSpaceController>();
        ss->setDimensions(cfg.ss_io.num_states, cfg.ss_io.num_inputs);
        s->ctrl = std::move(ss);
    } else {
        // Unknown type
        s->ctrl.reset();
        return false;
    }
    
    return true;
}

bool ControlKernel::enableSlot(uint8_t slot, bool enable) {
    Slot* s = getSlot_(slot);
    if (!s || !s->ctrl) return false;
    
    s->cfg.enabled = enable;
    if (!enable) {
        s->ctrl->reset();
    }
    return true;
}

bool ControlKernel::resetSlot(uint8_t slot) {
    Slot* s = getSlot_(slot);
    if (!s || !s->ctrl) return false;
    
    s->ctrl->reset();
    s->status.last_error = nullptr;
    return true;
}

bool ControlKernel::setParam(uint8_t slot, const char* key, float value) {
    Slot* s = getSlot_(slot);
    if (!s || !s->ctrl) return false;
    
    return s->ctrl->setParam(key, value);
}

bool ControlKernel::setParamArray(uint8_t slot, const char* key, const float* values, size_t len) {
    Slot* s = getSlot_(slot);
    if (!s || !s->ctrl) return false;
    
    return s->ctrl->setParamArray(key, values, len);
}

SlotConfig ControlKernel::getConfig(uint8_t slot) const {
    const Slot* s = getSlot_(slot);
    if (!s) {
        SlotConfig empty;
        empty.slot = slot;
        return empty;
    }
    return s->cfg;
}

SlotStatus ControlKernel::getStatus(uint8_t slot) const {
    const Slot* s = getSlot_(slot);
    if (!s) return SlotStatus{};
    return s->status;
}

void ControlKernel::step(uint32_t now_ms, float dt_s, SignalBus& signals, bool is_armed, bool is_active) {
    // Check watchdog for stuck slots
    watchdog_.check(now_ms);

    for (auto& s : slots_) {
        if (!s.cfg.enabled || !s.ctrl) continue;

        // Check state gating
        if (s.cfg.require_armed && !is_armed) continue;
        if (s.cfg.require_active && !is_active) continue;

        // Check rate limiting
        uint32_t period_ms = 1000 / s.cfg.rate_hz;
        if (now_ms - s.last_step_ms < period_ms) continue;
        s.last_step_ms = now_ms;

        // Begin watchdog timing
        watchdog_.beginSlot(s.cfg.slot, now_ms);

        // Dispatch based on controller type
        if (s.ctrl->isMultiState()) {
            // State-space controller
            const auto& io = s.cfg.ss_io;
            
            float states[StateSpaceIO::MAX_STATES];
            float refs[StateSpaceIO::MAX_STATES];
            float outputs[StateSpaceIO::MAX_INPUTS];
            
            // Read state signals
            bool all_ok = true;
            for (uint8_t i = 0; i < io.num_states; i++) {
                if (!signals.get(io.state_ids[i], states[i])) {
                    s.status.last_error = "state_signal_missing";
                    s.status.ok = false;
                    all_ok = false;
                    break;
                }
                if (!signals.get(io.ref_ids[i], refs[i])) {
                    // Reference is optional - default to 0
                    refs[i] = 0.0f;
                }
            }
            
            if (!all_ok) continue;
            
            // Compute
            s.ctrl->computeMulti(states, refs, io.num_states, 
                                  outputs, io.num_inputs, 
                                  dt_s, signals, io);
            
            // Write output signals
            for (uint8_t j = 0; j < io.num_inputs; j++) {
                signals.set(io.output_ids[j], outputs[j], now_ms);
            }

            // End watchdog timing for multi-state
            watchdog_.endSlot(s.cfg.slot, now_ms);

        } else {
            // PID controller (single-input)
            float ref = 0.0f, meas = 0.0f;
            if (!signals.get(s.cfg.io.ref_id, ref)) {
                s.status.last_error = "ref_signal_missing";
                s.status.ok = false;
                continue;
            }
            if (!signals.get(s.cfg.io.meas_id, meas)) {
                s.status.last_error = "meas_signal_missing";
                s.status.ok = false;
                continue;
            }
            
            // Compute control output
            float out = s.ctrl->compute(ref, meas, dt_s);

            // Write output signal
            signals.set(s.cfg.io.out_id, out, now_ms);

            // End watchdog timing for single-state
            watchdog_.endSlot(s.cfg.slot, now_ms);
        }

        // Update status
        s.status.ok = true;
        s.status.run_count++;
        s.status.last_run_ms = now_ms;
        s.status.last_error = nullptr;
    }
}

void ControlKernel::resetAll() {
    for (auto& s : slots_) {
        if (s.ctrl) s.ctrl->reset();
        s.status = SlotStatus{};
    }
}

void ControlKernel::disableAll() {
    for (auto& s : slots_) {
        s.cfg.enabled = false;
        if (s.ctrl) s.ctrl->reset();
    }
}

// -----------------------------------------------------------------------------
// PidController Implementation
// -----------------------------------------------------------------------------

PidController::PidController(float kp, float ki, float kd)
    : kp_(kp), ki_(ki), kd_(kd) {}

float PidController::compute(float ref, float meas, float dt_s) {
    float error = ref - meas;
    
    // Proportional
    float p_term = kp_ * error;
    
    // Integral
    if (dt_s > 0.0f) {
        integral_ += error * dt_s;
        integral_ = std::max(i_min_, std::min(i_max_, integral_));
    }
    float i_term = ki_ * integral_;
    
    // Derivative
    float d_term = 0.0f;
    if (!first_run_ && dt_s > 0.0f) {
        d_term = kd_ * (error - prev_error_) / dt_s;
    }
    prev_error_ = error;
    first_run_ = false;
    
    // Sum and clamp
    float out = p_term + i_term + d_term;
    out = std::max(out_min_, std::min(out_max_, out));
    
    return out;
}

void PidController::reset() {
    integral_ = 0.0f;
    prev_error_ = 0.0f;
    first_run_ = true;
}

bool PidController::setParam(const char* key, float value) {
    if (!key) return false;
    
    if (strcmp(key, "kp") == 0) { kp_ = value; return true; }
    if (strcmp(key, "ki") == 0) { ki_ = value; return true; }
    if (strcmp(key, "kd") == 0) { kd_ = value; return true; }
    if (strcmp(key, "out_min") == 0) { out_min_ = value; return true; }
    if (strcmp(key, "out_max") == 0) { out_max_ = value; return true; }
    if (strcmp(key, "i_min") == 0) { i_min_ = value; return true; }
    if (strcmp(key, "i_max") == 0) { i_max_ = value; return true; }
    
    return false;
}

bool PidController::getParam(const char* key, float& value) const {
    if (!key) return false;
    
    if (strcmp(key, "kp") == 0) { value = kp_; return true; }
    if (strcmp(key, "ki") == 0) { value = ki_; return true; }
    if (strcmp(key, "kd") == 0) { value = kd_; return true; }
    if (strcmp(key, "out_min") == 0) { value = out_min_; return true; }
    if (strcmp(key, "out_max") == 0) { value = out_max_; return true; }
    if (strcmp(key, "i_min") == 0) { value = i_min_; return true; }
    if (strcmp(key, "i_max") == 0) { value = i_max_; return true; }
    
    return false;
}

void PidController::setGains(float kp, float ki, float kd) {
    kp_ = kp;
    ki_ = ki;
    kd_ = kd;
}

void PidController::setOutputLimits(float min_out, float max_out) {
    out_min_ = min_out;
    out_max_ = max_out;
}

void PidController::setIntegralLimits(float min_i, float max_i) {
    i_min_ = min_i;
    i_max_ = max_i;
}

// -----------------------------------------------------------------------------
// StateSpaceController Implementation
// -----------------------------------------------------------------------------

StateSpaceController::StateSpaceController() {
    // Initialize arrays to zero
    memset(K_, 0, sizeof(K_));
    memset(Kr_, 0, sizeof(Kr_));
    memset(Ki_, 0, sizeof(Ki_));
    memset(integrator_, 0, sizeof(integrator_));
    
    // Default limits
    for (size_t i = 0; i < MAX_INPUTS; i++) {
        integrator_min_[i] = -1.0f;
        integrator_max_[i] = 1.0f;
        u_min_[i] = -1.0f;
        u_max_[i] = 1.0f;
    }
}

void StateSpaceController::setDimensions(uint8_t num_states, uint8_t num_inputs) {
    num_states_ = std::min(num_states, (uint8_t)MAX_STATES);
    num_inputs_ = std::min(num_inputs, (uint8_t)MAX_INPUTS);
}

void StateSpaceController::computeMulti(
    const float* states, const float* refs, uint8_t num_states,
    float* outputs, uint8_t num_outputs,
    float dt_s, SignalBus& signals, const StateSpaceIO& io
) {
    (void)signals;  // Not used directly here
    (void)io;       // Configuration already in class
    
    // Ensure dimensions match
    uint8_t ns = std::min(num_states, num_states_);
    uint8_t ni = std::min(num_outputs, num_inputs_);
    
    // Compute error for integral action
    float errors[MAX_STATES];
    for (uint8_t i = 0; i < ns; i++) {
        errors[i] = refs[i] - states[i];
    }
    
    // Compute control for each output
    for (uint8_t j = 0; j < ni; j++) {
        float u = 0.0f;
        
        if (error_based_) {
            // u = -K * (x - xr) = -K * (-error) = K * error
            for (uint8_t i = 0; i < ns; i++) {
                u += K_[j * MAX_STATES + i] * errors[i];
            }
        } else {
            // u = -K * x + Kr * r
            for (uint8_t i = 0; i < ns; i++) {
                u -= K_[j * MAX_STATES + i] * states[i];
                u += Kr_[j * MAX_STATES + i] * refs[i];
            }
        }
        
        // Integral action (on first state error)
        if (Ki_[j] != 0.0f && dt_s > 0.0f) {
            integrator_[j] += errors[0] * dt_s;
            integrator_[j] = clamp(integrator_[j], integrator_min_[j], integrator_max_[j]);
            u += Ki_[j] * integrator_[j];
        }
        
        // Clamp output
        outputs[j] = clamp(u, u_min_[j], u_max_[j]);
    }
}

void StateSpaceController::reset() {
    memset(integrator_, 0, sizeof(integrator_));
}

bool StateSpaceController::setParam(const char* key, float value) {
    if (!key) return false;
    
    // Output limits: "u0_min", "u0_max", "u1_min", etc.
    if (strncmp(key, "u", 1) == 0 && strlen(key) >= 5) {
        uint8_t idx = key[1] - '0';
        if (idx >= MAX_INPUTS) return false;
        
        if (strstr(key, "_min")) { u_min_[idx] = value; return true; }
        if (strstr(key, "_max")) { u_max_[idx] = value; return true; }
    }
    
    // Integral limits: "i0_min", "i0_max", etc.
    if (strncmp(key, "i", 1) == 0 && strlen(key) >= 5) {
        uint8_t idx = key[1] - '0';
        if (idx >= MAX_INPUTS) return false;
        
        if (strstr(key, "_min")) { integrator_min_[idx] = value; return true; }
        if (strstr(key, "_max")) { integrator_max_[idx] = value; return true; }
    }
    
    // Integral gains: "ki0", "ki1"
    if (strncmp(key, "ki", 2) == 0 && strlen(key) == 3) {
        uint8_t idx = key[2] - '0';
        if (idx >= MAX_INPUTS) return false;
        Ki_[idx] = value;
        return true;
    }
    
    // Feedback mode
    if (strcmp(key, "error_based") == 0) {
        error_based_ = (value != 0.0f);
        return true;
    }
    
    // Individual K gains: "k00", "k01", "k10", etc. (row, col)
    if (key[0] == 'k' && strlen(key) == 3) {
        uint8_t row = key[1] - '0';
        uint8_t col = key[2] - '0';
        if (row >= MAX_INPUTS || col >= MAX_STATES) return false;
        K_[row * MAX_STATES + col] = value;
        return true;
    }
    
    // Individual Kr gains: "kr00", "kr01", etc.
    if (strncmp(key, "kr", 2) == 0 && strlen(key) == 4) {
        uint8_t row = key[2] - '0';
        uint8_t col = key[3] - '0';
        if (row >= MAX_INPUTS || col >= MAX_STATES) return false;
        Kr_[row * MAX_STATES + col] = value;
        return true;
    }
    
    return false;
}

bool StateSpaceController::getParam(const char* key, float& value) const {
    if (!key) return false;
    
    // Individual K gains
    if (key[0] == 'k' && strlen(key) == 3) {
        uint8_t row = key[1] - '0';
        uint8_t col = key[2] - '0';
        if (row >= MAX_INPUTS || col >= MAX_STATES) return false;
        value = K_[row * MAX_STATES + col];
        return true;
    }
    
    // Integral gains
    if (strncmp(key, "ki", 2) == 0 && strlen(key) == 3) {
        uint8_t idx = key[2] - '0';
        if (idx >= MAX_INPUTS) return false;
        value = Ki_[idx];
        return true;
    }
    
    return false;
}

bool StateSpaceController::setParamArray(const char* key, const float* values, size_t len) {
    if (!key || !values) return false;
    
    // Full K matrix
    if (strcmp(key, "K") == 0) {
        size_t max_len = num_inputs_ * num_states_;
        size_t copy_len = std::min(len, max_len);
        for (size_t i = 0; i < copy_len; i++) {
            K_[i] = values[i];
        }
        return true;
    }
    
    // Full Kr matrix
    if (strcmp(key, "Kr") == 0) {
        size_t max_len = num_inputs_ * num_states_;
        size_t copy_len = std::min(len, max_len);
        for (size_t i = 0; i < copy_len; i++) {
            Kr_[i] = values[i];
        }
        return true;
    }
    
    // Ki array
    if (strcmp(key, "Ki") == 0) {
        size_t copy_len = std::min(len, (size_t)num_inputs_);
        for (size_t i = 0; i < copy_len; i++) {
            Ki_[i] = values[i];
        }
        return true;
    }
    
    return false;
}

void StateSpaceController::setGainK(const float* K, size_t len) {
    setParamArray("K", K, len);
}

void StateSpaceController::setGainKr(const float* Kr, size_t len) {
    setParamArray("Kr", Kr, len);
}

void StateSpaceController::setGainKi(const float* Ki, size_t len) {
    setParamArray("Ki", Ki, len);
}

void StateSpaceController::setOutputLimits(uint8_t idx, float min_val, float max_val) {
    if (idx >= MAX_INPUTS) return;
    u_min_[idx] = min_val;
    u_max_[idx] = max_val;
}

void StateSpaceController::setIntegralLimits(uint8_t idx, float min_val, float max_val) {
    if (idx >= MAX_INPUTS) return;
    integrator_min_[idx] = min_val;
    integrator_max_[idx] = max_val;
}

void StateSpaceController::setFeedbackMode(bool error_based) {
    error_based_ = error_based;
}

bool ControlKernel::getParam(uint8_t slot, const char* key, float& value) const {
    const Slot* s = getSlot_(slot);
    if (!s || !s->ctrl) return false;
    return s->ctrl->getParam(key, value);
}

// -----------------------------------------------------------------------------
// ControlWatchdog Implementation
// -----------------------------------------------------------------------------

void ControlWatchdog::beginSlot(uint8_t slot, uint32_t now_ms) {
    if (slot >= MAX_SLOTS) return;
    slots_[slot].start_ms = now_ms;
    slots_[slot].in_progress = true;
}

void ControlWatchdog::endSlot(uint8_t slot, uint32_t now_ms) {
    if (slot >= MAX_SLOTS) return;
    auto& s = slots_[slot];
    if (!s.in_progress) return;

    uint32_t elapsed = now_ms - s.start_ms;
    if (elapsed > s.max_exec_ms) {
        s.max_exec_ms = elapsed;
    }
    s.in_progress = false;
    s.last_complete_ms = now_ms;
}

void ControlWatchdog::check(uint32_t now_ms) {
    if (timeout_ms_ == 0) return;  // Disabled

    for (uint8_t i = 0; i < MAX_SLOTS; i++) {
        auto& s = slots_[i];
        if (!s.in_progress) continue;

        uint32_t elapsed = now_ms - s.start_ms;
        if (elapsed >= timeout_ms_) {
            // Slot is stuck
            if (callback_) {
                callback_(i, elapsed);
            }
            // Mark as no longer in progress to avoid repeated callbacks
            s.in_progress = false;
        }
    }
}

uint32_t ControlWatchdog::getMaxExecTime(uint8_t slot) const {
    if (slot >= MAX_SLOTS) return 0;
    return slots_[slot].max_exec_ms;
}

void ControlWatchdog::resetStats() {
    for (auto& s : slots_) {
        s.max_exec_ms = 0;
    }
}