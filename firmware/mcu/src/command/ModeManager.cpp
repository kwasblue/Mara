// src/core/ModeManager.cpp

#include "command/ModeManager.h"
#include "core/CriticalSection.h"
#include <Arduino.h>
#include <cmath>

const char* maraModeToString(MaraMode m) {
    switch (m) {
        case MaraMode::BOOT:         return "BOOT";
        case MaraMode::DISCONNECTED: return "DISCONNECTED";
        case MaraMode::IDLE:         return "IDLE";
        case MaraMode::ARMED:        return "ARMED";
        case MaraMode::ACTIVE:       return "ACTIVE";
        case MaraMode::ESTOPPED:     return "ESTOPPED";
        default:                      return "UNKNOWN";
    }
}

void ModeManager::begin() {
    // Watchdog timeout: 2 seconds (was 5s - reduced for faster fault detection)
    // If the main loop hangs for >2s, MCU will reset
    if (halWatchdog_) {
        halWatchdog_->begin(2, true);
        halWatchdog_->addCurrentTask();
    }

    // Configure safety pins via HAL
    if (halGpio_) {
        if (cfg_.estop_pin >= 0) {
            halGpio_->pinMode(cfg_.estop_pin, hal::PinMode::InputPullup);
        }
        if (cfg_.bypass_pin >= 0) {
            halGpio_->pinMode(cfg_.bypass_pin, hal::PinMode::InputPullup);
        }
        if (cfg_.relay_pin >= 0) {
            halGpio_->pinMode(cfg_.relay_pin, hal::PinMode::Output);
            halGpio_->digitalWrite(cfg_.relay_pin, 0);
        }
    }

    mode_ = MaraMode::DISCONNECTED;
}

void ModeManager::update(uint32_t now_ms) {
    if (halWatchdog_) {
        halWatchdog_->reset();
    }
    readHardwareInputs();

    // Host timeout
    if (hostEverSeen_ && isConnected() && !isEstopped()) {
        uint32_t dt = now_ms - lastHostHeartbeat_;
        if (dt > cfg_.host_timeout_ms) {
            mara::CriticalSection lock(lock_);
            triggerStop();

            if (mode_ == MaraMode::ACTIVE) {
                mode_ = MaraMode::ARMED;     // fall back from ACTIVE
            } else if (mode_ == MaraMode::ARMED) {
                mode_ = MaraMode::ARMED;     // stay ARMED (don't disarm)
            } else {
                mode_ = MaraMode::IDLE;
            }

            lastHostHeartbeat_ = now_ms;      // prevent retrigger spam
        }
    }

    // Motion timeout (only in ACTIVE and only if robot was actually moving)
    // This prevents timeout spam during testing when no motion is commanded
    if (mode_ == MaraMode::ACTIVE && lastMotionCmd_ > 0 && wasMoving_) {
        uint32_t dtm = now_ms - lastMotionCmd_;
        if (dtm > cfg_.motion_timeout_ms) {
            mara::CriticalSection lock(lock_);
            triggerStop();
            mode_ = MaraMode::ARMED;
            wasMoving_ = false;

            // Prevent re-triggering every loop iteration
            lastMotionCmd_ = now_ms;
        }
    }
    if (mode_ != lastLoggedMode_) {
        Serial.printf("[MODE] %s -> %s  hostAge=%lu  motionAge=%lu\n",
            maraModeToString(lastLoggedMode_),
            maraModeToString(mode_),
            (unsigned long)hostAgeMs(now_ms),
            (unsigned long)motionAgeMs(now_ms)
        );
        lastLoggedMode_ = mode_;
    }

    // Relay control via HAL
    if (cfg_.relay_pin >= 0 && halGpio_) {
        bool allow = canMove() && !isEstopped();
        halGpio_->digitalWrite(cfg_.relay_pin, allow ? 1 : 0);
    }
}

void ModeManager::readHardwareInputs() {
    if (!halGpio_) return;

    if (cfg_.bypass_pin >= 0) {
        bypassed_ = (halGpio_->digitalRead(cfg_.bypass_pin) == 0);
    }
    if (cfg_.estop_pin >= 0) {
        if (halGpio_->digitalRead(cfg_.estop_pin) == 0 && !isEstopped()) {
            estop();
        }
    }
}

void ModeManager::onHostHeartbeat(uint32_t now_ms) {
    lastHostHeartbeat_ = now_ms;
    stopLatched_ = false;  // host contact recovered; allow future stop episode logs/callbacks

    if (!hostEverSeen_) {
        hostEverSeen_ = true;
    }

    if (mode_ == MaraMode::DISCONNECTED) {
        mode_ = MaraMode::IDLE;
    }
}

void ModeManager::onMotionCommand(uint32_t now_ms, float vx, float omega) {
    lastMotionCmd_ = now_ms;
    // Track if actual motion was commanded (non-zero velocity)
    // Motion timeout only applies if robot was actually moving
    if (fabsf(vx) > 0.001f || fabsf(omega) > 0.001f) {
        wasMoving_ = true;
    }
}

bool ModeManager::canTransition(MaraMode from, MaraMode to) {
    switch (from) {
        case MaraMode::BOOT:
            return to == MaraMode::DISCONNECTED;
        case MaraMode::DISCONNECTED:
            return to == MaraMode::IDLE || to == MaraMode::ESTOPPED;
        case MaraMode::IDLE:
            return to == MaraMode::ARMED || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ARMED:
            return to == MaraMode::IDLE || to == MaraMode::ACTIVE || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ACTIVE:
            return to == MaraMode::ARMED || to == MaraMode::DISCONNECTED || to == MaraMode::ESTOPPED;
        case MaraMode::ESTOPPED:
            return to == MaraMode::IDLE;
        default:
            return false;
    }
}

void ModeManager::arm() {
    mara::CriticalSection lock(lock_);
    stopLatched_ = false;
    if (mode_ == MaraMode::IDLE) {
        mode_ = MaraMode::ARMED;
    }
}

void ModeManager::activate() {
    mara::CriticalSection lock(lock_);
    stopLatched_ = false;
    if (mode_ == MaraMode::ARMED) {
        lastMotionCmd_ = now_ms();
        mode_ = MaraMode::ACTIVE;
    }
}

void ModeManager::deactivate() {
    mara::CriticalSection lock(lock_);
    if (mode_ == MaraMode::ACTIVE) {
        triggerStop();
        mode_ = MaraMode::ARMED;
        lastMotionCmd_ = now_ms();
    }
}

void ModeManager::disarm() {
    mara::CriticalSection lock(lock_);
    if (mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE) {
        triggerStop();
        mode_ = MaraMode::IDLE;
    }
}

void ModeManager::estop() {
    mara::CriticalSection lock(lock_);
    // Emergency stop: trigger both normal and emergency callbacks
    triggerStop();
    triggerEmergencyStop();  // Direct motor disable - doesn't rely on motion controller
    mode_ = MaraMode::ESTOPPED;
}

bool ModeManager::clearEstop() {
    mara::CriticalSection lock(lock_);
    stopLatched_ = false;
    if (!isEstopped()) {
        return true;
    }

    // Hardware E-stop must be released
    if (cfg_.estop_pin >= 0 && halGpio_) {
        if (halGpio_->digitalRead(cfg_.estop_pin) == 0) {
            return false;
        }
    }

    mode_ = MaraMode::IDLE;
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
    if (bypassed_) return;
    if (stopLatched_) return;
    stopLatched_ = true;
    if (stopCallback_) stopCallback_();
}

void ModeManager::triggerEmergencyStop() {
    // Emergency stop bypasses the bypass flag - always stops motors
    if (emergencyStopCallback_) emergencyStopCallback_();
}
