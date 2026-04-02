// src/core/ModeManager.cpp

#include "command/ModeManager.h"
#include "core/CriticalSection.h"
#include <Arduino.h>
#include <cmath>

const char* maraModeToString(MaraMode m) {
    switch (m) {
        case MaraMode::BOOT: return "BOOT";
        case MaraMode::DISCONNECTED: return "DISCONNECTED";
        case MaraMode::IDLE: return "IDLE";
        case MaraMode::ARMED: return "ARMED";
        case MaraMode::ACTIVE: return "ACTIVE";
        case MaraMode::ESTOPPED: return "ESTOPPED";
        default: return "UNKNOWN";
    }
}

void ModeManager::begin() {
    stats_ = {};
    hostTimedOut_ = false;
    if (halWatchdog_) {
        halWatchdog_->begin(2, true);
        halWatchdog_->addCurrentTask();
    }
    if (halGpio_) {
        if (cfg_.estop_pin >= 0) halGpio_->pinMode(cfg_.estop_pin, hal::PinMode::InputPullup);
        if (cfg_.bypass_pin >= 0) halGpio_->pinMode(cfg_.bypass_pin, hal::PinMode::InputPullup);
        if (cfg_.relay_pin >= 0) {
            halGpio_->pinMode(cfg_.relay_pin, hal::PinMode::Output);
            halGpio_->digitalWrite(cfg_.relay_pin, 0);
        }
    }
    mode_ = MaraMode::DISCONNECTED;
    if (persistentStateCallback_) persistentStateCallback_();
}

void ModeManager::update(uint32_t now_ms) {
    if (halWatchdog_) halWatchdog_->reset();
    readHardwareInputs();

    // Host timeout: 0 = disabled
    if (cfg_.host_timeout_ms > 0 && hostEverSeen_ && isConnected() && !isEstopped()) {
        uint32_t dt = now_ms - lastHostHeartbeat_;
        if (dt > cfg_.host_timeout_ms) {
            mara::CriticalSection lock(lock_);
            triggerStop();
            // Downgrade only ACTIVE->ARMED on host timeout
            // Leave ARMED as-is, don't touch DISCONNECTED or other states
            if (mode_ == MaraMode::ACTIVE) {
                mode_ = MaraMode::ARMED;
            }
            // ARMED stays ARMED, IDLE stays IDLE, DISCONNECTED stays DISCONNECTED
            hostTimedOut_ = true;
            stats_.host_timeout_count++;
            stats_.last_host_timeout_ms = now_ms;
            if (dt > stats_.max_host_gap_ms) stats_.max_host_gap_ms = dt;
            stats_.last_fault = 1;
            lastHostHeartbeat_ = now_ms;
            if (persistentStateCallback_) persistentStateCallback_();
        }
    }

    // Motion timeout: 0 = disabled
    if (cfg_.motion_timeout_ms > 0 && mode_ == MaraMode::ACTIVE && lastMotionCmd_ > 0 && wasMoving_) {
        uint32_t dtm = now_ms - lastMotionCmd_;
        if (dtm > cfg_.motion_timeout_ms) {
            mara::CriticalSection lock(lock_);
            triggerStop();
            mode_ = MaraMode::ARMED;
            wasMoving_ = false;
            stats_.motion_timeout_count++;
            stats_.last_motion_timeout_ms = now_ms;
            if (dtm > stats_.max_motion_gap_ms) stats_.max_motion_gap_ms = dtm;
            stats_.last_fault = 2;
            lastMotionCmd_ = now_ms;
            if (persistentStateCallback_) persistentStateCallback_();
        }
    }

    if (mode_ != lastLoggedMode_) {
        Serial.printf("[MODE] %s -> %s  hostAge=%lu  motionAge=%lu\n", maraModeToString(lastLoggedMode_), maraModeToString(mode_), (unsigned long)hostAgeMs(now_ms), (unsigned long)motionAgeMs(now_ms));
        lastLoggedMode_ = mode_;
    }

    if (cfg_.relay_pin >= 0 && halGpio_) {
        bool allow = canMove() && !isEstopped();
        halGpio_->digitalWrite(cfg_.relay_pin, allow ? 1 : 0);
    }
}

void ModeManager::readHardwareInputs() {
    if (!halGpio_) return;
    if (cfg_.bypass_pin >= 0) bypassed_ = (halGpio_->digitalRead(cfg_.bypass_pin) == 0);
    if (cfg_.estop_pin >= 0 && halGpio_->digitalRead(cfg_.estop_pin) == 0 && !isEstopped()) estop();
}

void ModeManager::onHostHeartbeat(uint32_t now_ms) {
    if (hostEverSeen_) {
        const uint32_t gap = now_ms - lastHostHeartbeat_;
        if (gap > stats_.max_host_gap_ms) stats_.max_host_gap_ms = gap;
    }
    if (hostTimedOut_) {
        stats_.host_recovery_count++;
        hostTimedOut_ = false;
    }
    lastHostHeartbeat_ = now_ms;
    stats_.last_host_heartbeat_ms = now_ms;
    stats_.host_heartbeat_count++;
    stopLatched_ = false;
    if (!hostEverSeen_) hostEverSeen_ = true;
    if (mode_ == MaraMode::DISCONNECTED) mode_ = MaraMode::IDLE;

    // Heartbeats also reset motion timeout - if host is alive, keep MCU active
    // This prevents timeout when using servo/GPIO commands that aren't velocity-based
    if (lastMotionCmd_ > 0) {
        lastMotionCmd_ = now_ms;
    }

    if (persistentStateCallback_) persistentStateCallback_();
}

void ModeManager::onMotionCommand(uint32_t now_ms, float vx, float omega) {
    if (lastMotionCmd_ > 0) {
        const uint32_t gap = now_ms - lastMotionCmd_;
        if (gap > stats_.max_motion_gap_ms) stats_.max_motion_gap_ms = gap;
    }
    lastMotionCmd_ = now_ms;
    stats_.last_motion_command_ms = now_ms;
    stats_.motion_command_count++;
    if (fabsf(vx) > 0.001f || fabsf(omega) > 0.001f) wasMoving_ = true;
}

bool ModeManager::canTransition(MaraMode from, MaraMode to) {
    switch (from) {
        case MaraMode::BOOT: return to == MaraMode::DISCONNECTED;
        case MaraMode::DISCONNECTED: return to == MaraMode::IDLE || to == MaraMode::ESTOPPED;
        case MaraMode::IDLE: return to == MaraMode::ARMED || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ARMED: return to == MaraMode::IDLE || to == MaraMode::ACTIVE || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ACTIVE: return to == MaraMode::ARMED || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ESTOPPED: return to == MaraMode::IDLE;
        default: return false;
    }
}

void ModeManager::arm() { mara::CriticalSection lock(lock_); stopLatched_ = false; if (mode_ == MaraMode::IDLE) mode_ = MaraMode::ARMED; }
void ModeManager::activate(uint32_t now_ms) { mara::CriticalSection lock(lock_); stopLatched_ = false; if (mode_ == MaraMode::ARMED) { lastMotionCmd_ = now_ms; mode_ = MaraMode::ACTIVE; } }
void ModeManager::deactivate(uint32_t now_ms) { mara::CriticalSection lock(lock_); if (mode_ == MaraMode::ACTIVE) { triggerStop(); mode_ = MaraMode::ARMED; lastMotionCmd_ = now_ms; } }
void ModeManager::disarm() { mara::CriticalSection lock(lock_); if (mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE) { triggerStop(); mode_ = MaraMode::IDLE; } }
void ModeManager::estop() { mara::CriticalSection lock(lock_); triggerStop(); triggerEmergencyStop(); mode_ = MaraMode::ESTOPPED; stats_.last_fault = 3; if (persistentStateCallback_) persistentStateCallback_(); }

bool ModeManager::clearEstop() {
    mara::CriticalSection lock(lock_);
    stopLatched_ = false;
    if (!isEstopped()) return true;
    if (cfg_.estop_pin >= 0 && halGpio_ && halGpio_->digitalRead(cfg_.estop_pin) == 0) return false;
    mode_ = MaraMode::IDLE;
    if (persistentStateCallback_) persistentStateCallback_();
    return true;
}

bool ModeManager::validateVelocity(float vx, float omega, float& out_vx, float& out_omega) {
    if (std::isnan(vx) || std::isinf(vx) || std::isnan(omega) || std::isinf(omega)) {
        out_vx = 0;
        out_omega = 0;
        return false;
    }
    out_vx = constrain(vx, -cfg_.max_linear_vel, cfg_.max_linear_vel);
    out_omega = constrain(omega, -cfg_.max_angular_vel, cfg_.max_angular_vel);
    return true;
}

void ModeManager::triggerStop() {
    if (bypassed_ || stopLatched_) return;
    stopLatched_ = true;
    if (stopCallback_) stopCallback_();
}

void ModeManager::triggerEmergencyStop() {
    if (emergencyStopCallback_) emergencyStopCallback_();
}
