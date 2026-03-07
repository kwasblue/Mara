// src/core/Observer.cpp
// State observer implementation

#include "config/FeatureFlags.h"

#if HAS_OBSERVER

#include "control/Observer.h"
#include "control/SignalBus.h"
#include <cstring>
#include <cmath>

// -----------------------------------------------------------------------------
// LuenbergerObserver Implementation
// -----------------------------------------------------------------------------

void LuenbergerObserver::configure(uint8_t num_states, uint8_t num_inputs, uint8_t num_outputs) {
    num_states_ = std::min(num_states, (uint8_t)MAX_STATES);
    num_inputs_ = std::min(num_inputs, (uint8_t)MAX_INPUTS);
    num_outputs_ = std::min(num_outputs, (uint8_t)MAX_OUTPUTS);
    reset();
}

void LuenbergerObserver::update(const float* u, const float* y, float dt, float* x_hat_out) {
    if (dt <= 0.0f) dt = 0.001f;
    
    // Clamp dt to prevent instability
    dt = clamp(dt, 0.0001f, 0.1f);
    
    const uint8_t n = num_states_;
    const uint8_t m = num_inputs_;
    const uint8_t p = num_outputs_;
    
    // Step 1: Compute dx = A·x̂ + B·u (continuous-time derivative)
    float dx[MAX_STATES] = {0};
    
    // dx = A·x̂
    for (uint8_t i = 0; i < n; i++) {
        float sum = 0.0f;
        for (uint8_t j = 0; j < n; j++) {
            sum += A_[i * MAX_STATES + j] * x_hat_[j];
        }
        dx[i] = sum;
    }
    
    // dx += B·u
    for (uint8_t i = 0; i < n; i++) {
        for (uint8_t j = 0; j < m; j++) {
            dx[i] += B_[i * MAX_INPUTS + j] * u[j];
        }
    }
    
    // Step 2: Predict x̂⁻ = x̂ + dx·dt (Euler integration)
    float x_pred[MAX_STATES];
    for (uint8_t i = 0; i < n; i++) {
        x_pred[i] = x_hat_[i] + dx[i] * dt;
    }
    
    // Step 3: Compute output prediction ŷ = C·x̂⁻
    float y_pred[MAX_OUTPUTS] = {0};
    for (uint8_t i = 0; i < p; i++) {
        for (uint8_t j = 0; j < n; j++) {
            y_pred[i] += C_[i * MAX_STATES + j] * x_pred[j];
        }
    }
    
    // Step 4: Compute innovation (measurement error) e = y - ŷ
    float error[MAX_OUTPUTS];
    for (uint8_t i = 0; i < p; i++) {
        error[i] = y[i] - y_pred[i];
    }
    
    // Step 5: Correct x̂ = x̂⁻ + L·e
    for (uint8_t i = 0; i < n; i++) {
        float correction = 0.0f;
        for (uint8_t j = 0; j < p; j++) {
            correction += L_[i * MAX_OUTPUTS + j] * error[j];
        }
        x_hat_[i] = x_pred[i] + correction;
    }
    
    // Copy to output
    for (uint8_t i = 0; i < n; i++) {
        x_hat_out[i] = x_hat_[i];
    }
    
    initialized_ = true;
}

void LuenbergerObserver::reset() {
    memset(x_hat_, 0, sizeof(x_hat_));
    initialized_ = false;
}

void LuenbergerObserver::initState(const float* x0) {
    for (uint8_t i = 0; i < num_states_; i++) {
        x_hat_[i] = x0[i];
    }
    initialized_ = true;
}

void LuenbergerObserver::setState(uint8_t idx, float value) {
    if (idx < num_states_) {
        x_hat_[idx] = value;
    }
}

float LuenbergerObserver::getState(uint8_t idx) const {
    return (idx < num_states_) ? x_hat_[idx] : 0.0f;
}

bool LuenbergerObserver::setA(const float* A, size_t len) {
    memset(A_, 0, sizeof(A_));
    size_t max_len = num_states_ * num_states_;
    size_t copy_len = std::min(len, max_len);
    
    // Copy row by row to handle MAX_STATES stride
    for (uint8_t i = 0; i < num_states_; i++) {
        for (uint8_t j = 0; j < num_states_; j++) {
            size_t src_idx = i * num_states_ + j;
            if (src_idx < copy_len) {
                A_[i * MAX_STATES + j] = A[src_idx];
            }
        }
    }
    return true;
}

bool LuenbergerObserver::setB(const float* B, size_t len) {
    memset(B_, 0, sizeof(B_));
    size_t max_len = num_states_ * num_inputs_;
    size_t copy_len = std::min(len, max_len);
    
    for (uint8_t i = 0; i < num_states_; i++) {
        for (uint8_t j = 0; j < num_inputs_; j++) {
            size_t src_idx = i * num_inputs_ + j;
            if (src_idx < copy_len) {
                B_[i * MAX_INPUTS + j] = B[src_idx];
            }
        }
    }
    return true;
}

bool LuenbergerObserver::setC(const float* C, size_t len) {
    memset(C_, 0, sizeof(C_));
    size_t max_len = num_outputs_ * num_states_;
    size_t copy_len = std::min(len, max_len);
    
    for (uint8_t i = 0; i < num_outputs_; i++) {
        for (uint8_t j = 0; j < num_states_; j++) {
            size_t src_idx = i * num_states_ + j;
            if (src_idx < copy_len) {
                C_[i * MAX_STATES + j] = C[src_idx];
            }
        }
    }
    return true;
}

bool LuenbergerObserver::setL(const float* L, size_t len) {
    memset(L_, 0, sizeof(L_));
    size_t max_len = num_states_ * num_outputs_;
    size_t copy_len = std::min(len, max_len);
    
    for (uint8_t i = 0; i < num_states_; i++) {
        for (uint8_t j = 0; j < num_outputs_; j++) {
            size_t src_idx = i * num_outputs_ + j;
            if (src_idx < copy_len) {
                L_[i * MAX_OUTPUTS + j] = L[src_idx];
            }
        }
    }
    return true;
}

bool LuenbergerObserver::setParam(const char* key, float value) {
    if (!key || strlen(key) < 3) return false;
    
    char matrix = key[0];
    uint8_t row = key[1] - '0';
    uint8_t col = key[2] - '0';
    
    switch (matrix) {
        case 'A': case 'a':
            if (row < num_states_ && col < num_states_) {
                A_[row * MAX_STATES + col] = value;
                return true;
            }
            break;
        case 'B': case 'b':
            if (row < num_states_ && col < num_inputs_) {
                B_[row * MAX_INPUTS + col] = value;
                return true;
            }
            break;
        case 'C': case 'c':
            if (row < num_outputs_ && col < num_states_) {
                C_[row * MAX_STATES + col] = value;
                return true;
            }
            break;
        case 'L': case 'l':
            if (row < num_states_ && col < num_outputs_) {
                L_[row * MAX_OUTPUTS + col] = value;
                return true;
            }
            break;
    }
    return false;
}

bool LuenbergerObserver::setParamArray(const char* key, const float* values, size_t len) {
    if (!key || !values || len == 0) return false;
    
    if (strcmp(key, "A") == 0 || strcmp(key, "a") == 0) return setA(values, len);
    if (strcmp(key, "B") == 0 || strcmp(key, "b") == 0) return setB(values, len);
    if (strcmp(key, "C") == 0 || strcmp(key, "c") == 0) return setC(values, len);
    if (strcmp(key, "L") == 0 || strcmp(key, "l") == 0) return setL(values, len);
    
    return false;
}

// -----------------------------------------------------------------------------
// ObserverManager Implementation
// -----------------------------------------------------------------------------

bool ObserverManager::configure(uint8_t slot, const ObserverConfig& config, uint16_t rate_hz) {
    if (slot >= MAX_OBSERVERS) return false;
    
    auto& s = slots_[slot];
    s.config = config;
    s.rate_hz = std::max((uint16_t)1, rate_hz);
    s.observer.configure(config.num_states, config.num_inputs, config.num_outputs);
    s.configured = true;
    s.enabled = false;
    s.update_count = 0;
    return true;
}

bool ObserverManager::enable(uint8_t slot, bool en) {
    if (slot >= MAX_OBSERVERS || !slots_[slot].configured) return false;
    
    slots_[slot].enabled = en;
    if (!en) {
        slots_[slot].observer.reset();
    }
    return true;
}

bool ObserverManager::reset(uint8_t slot) {
    if (slot >= MAX_OBSERVERS) return false;
    
    slots_[slot].observer.reset();
    slots_[slot].update_count = 0;
    return true;
}

bool ObserverManager::setParam(uint8_t slot, const char* key, float value) {
    if (slot >= MAX_OBSERVERS) return false;
    return slots_[slot].observer.setParam(key, value);
}

bool ObserverManager::setParamArray(uint8_t slot, const char* key, const float* values, size_t len) {
    if (slot >= MAX_OBSERVERS) return false;
    return slots_[slot].observer.setParamArray(key, values, len);
}

void ObserverManager::step(uint32_t now_ms, float dt_s, SignalBus& signals) {
    for (size_t i = 0; i < MAX_OBSERVERS; i++) {
        auto& s = slots_[i];
        if (!s.configured || !s.enabled) continue;
        
        // Rate limiting
        uint32_t period_ms = 1000 / s.rate_hz;
        if (now_ms - s.last_update_ms < period_ms) continue;
        
        // Compute actual dt from last update
        float actual_dt = (s.last_update_ms > 0) 
            ? (now_ms - s.last_update_ms) / 1000.0f 
            : dt_s;
        s.last_update_ms = now_ms;
        
        const auto& cfg = s.config;
        
        // Read control inputs (u)
        float u[ObserverConfig::MAX_INPUTS] = {0};
        for (uint8_t j = 0; j < cfg.num_inputs; j++) {
            if (cfg.input_ids[j] != 0) {
                signals.get(cfg.input_ids[j], u[j]);
            }
        }
        
        // Read measurements (y)
        float y[ObserverConfig::MAX_OUTPUTS] = {0};
        for (uint8_t j = 0; j < cfg.num_outputs; j++) {
            if (cfg.output_ids[j] != 0) {
                signals.get(cfg.output_ids[j], y[j]);
            }
        }
        
        // Initialize from measurement on first run
        if (!s.observer.isInitialized()) {
            float x0[ObserverConfig::MAX_STATES] = {0};
            // Set measured states from y (assuming C selects first states)
            for (uint8_t j = 0; j < cfg.num_outputs && j < cfg.num_states; j++) {
                x0[j] = y[j];
            }
            s.observer.initState(x0);
        }
        
        // Run observer
        float x_hat[ObserverConfig::MAX_STATES];
        s.observer.update(u, y, actual_dt, x_hat);
        
        // Write estimates to signal bus
        for (uint8_t j = 0; j < cfg.num_states; j++) {
            if (cfg.estimate_ids[j] != 0) {
                signals.set(cfg.estimate_ids[j], x_hat[j], now_ms);
            }
        }
        
        s.update_count++;
    }
}

LuenbergerObserver* ObserverManager::getObserver(uint8_t slot) {
    if (slot >= MAX_OBSERVERS) return nullptr;
    return &slots_[slot].observer;
}

const ObserverManager::Slot& ObserverManager::getSlot(uint8_t slot) const {
    static Slot empty;
    if (slot >= MAX_OBSERVERS) return empty;
    return slots_[slot];
}

void ObserverManager::resetAll() {
    for (auto& s : slots_) {
        s.observer.reset();
        s.update_count = 0;
    }
}

void ObserverManager::disableAll() {
    for (auto& s : slots_) {
        s.enabled = false;
        s.observer.reset();
    }
}

#endif // HAS_OBSERVER