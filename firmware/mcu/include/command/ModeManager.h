// include/core/ModeManager.h

#pragma once
#include <cstdint>
#include <functional>
#include "core/Clock.h"
#include "core/CriticalSection.h"
#include "hal/IGpio.h"
#include "hal/IWatchdog.h"

enum class MaraMode : uint8_t {
    BOOT,
    DISCONNECTED,
    IDLE,
    ARMED,
    ACTIVE,
    ESTOPPED
};

const char* maraModeToString(MaraMode m);

struct SafetyConfig {
    uint32_t host_timeout_ms = 3000;
    uint32_t motion_timeout_ms = 500;
    float max_linear_vel = 2.0f;
    float max_angular_vel = 3.14f;
    int estop_pin = -1;
    int bypass_pin = -1;
    int relay_pin = -1;
};

struct ModeWatchdogStats {
    uint32_t host_heartbeat_count = 0;
    uint32_t host_timeout_count = 0;
    uint32_t host_recovery_count = 0;
    uint32_t motion_command_count = 0;
    uint32_t motion_timeout_count = 0;
    uint32_t last_host_heartbeat_ms = 0;
    uint32_t last_motion_command_ms = 0;
    uint32_t last_host_timeout_ms = 0;
    uint32_t last_motion_timeout_ms = 0;
    uint32_t max_host_gap_ms = 0;
    uint32_t max_motion_gap_ms = 0;
    uint8_t last_fault = 0;
};

class ModeManager {
public:
    using StopCallback = std::function<void()>;

    ModeManager() {
#ifdef ESP32
        spinlock_initialize(&lock_);
#endif
    }
    
    void configure(const SafetyConfig& cfg) { cfg_ = cfg; }
    void begin();
    void update(uint32_t now_ms);
    
    // Watchdog feeds
    void onHostHeartbeat(uint32_t now_ms);
    void onMotionCommand(uint32_t now_ms, float vx = 0.0f, float omega = 0.0f);
    
    // Transitions
    void arm();
    void activate(uint32_t now_ms);
    void deactivate(uint32_t now_ms);
    void disarm();
    void estop();
    bool clearEstop();
    
    // Queries
    MaraMode mode() const { return mode_; }
    bool canMove() const { return mode_ == MaraMode::ARMED || mode_ == MaraMode::ACTIVE; }
    bool isEstopped() const { return mode_ == MaraMode::ESTOPPED; }
    bool isConnected() const { return mode_ != MaraMode::BOOT && mode_ != MaraMode::DISCONNECTED; }
    bool isBypassed() const { return bypassed_; }
    uint32_t hostAgeMs(uint32_t now_ms) const { return now_ms - lastHostHeartbeat_; }
    uint32_t motionAgeMs(uint32_t now_ms) const { return now_ms - lastMotionCmd_; }
    const ModeWatchdogStats& watchdogStats() const { return stats_; }
    
    // Validation
    bool validateVelocity(float vx, float omega, float& out_vx, float& out_omega);
    
    // Callback
    void onStop(StopCallback cb) { stopCallback_ = cb; }
    void onEmergencyStop(StopCallback cb) { emergencyStopCallback_ = cb; }
    void onPersistentStateChanged(StopCallback cb) { persistentStateCallback_ = cb; }

    // Runtime timeout control (0 = disabled)
    void setTimeouts(uint32_t host_ms, uint32_t motion_ms) {
        cfg_.host_timeout_ms = host_ms;
        cfg_.motion_timeout_ms = motion_ms;
    }
    uint32_t getHostTimeout() const { return cfg_.host_timeout_ms; }
    uint32_t getMotionTimeout() const { return cfg_.motion_timeout_ms; }
    bool timeoutsEnabled() const { return cfg_.host_timeout_ms > 0 || cfg_.motion_timeout_ms > 0; }

    // Clock injection for testability
    void setClock(mara::IClock* clk) { clock_ = clk; }
    void setHalGpio(hal::IGpio* gpio) { halGpio_ = gpio; }
    void setHalWatchdog(hal::IWatchdog* watchdog) { halWatchdog_ = watchdog; }

private:
    hal::IGpio*     halGpio_     = nullptr;
    hal::IWatchdog* halWatchdog_ = nullptr;
    SafetyConfig cfg_;
    MaraMode mode_ = MaraMode::BOOT;
    MaraMode lastLoggedMode_ = MaraMode::BOOT;

    uint32_t lastHostHeartbeat_ = 0;
    uint32_t lastMotionCmd_ = 0;
    bool hostEverSeen_ = false;
    bool bypassed_ = false;
    bool wasMoving_ = false;
    bool stopLatched_ = false;
    bool hostTimedOut_ = false;
    ModeWatchdogStats stats_{};

    StopCallback stopCallback_;
    StopCallback emergencyStopCallback_;
    StopCallback persistentStateCallback_;
    mara::IClock* clock_ = nullptr;

    uint32_t now_ms() const {
        if (clock_) return clock_->millis();
        return mara::getSystemClock().millis();
    }

    mara::SpinlockType lock_ = MCU_SPINLOCK_INIT;

    void triggerStop();
    void triggerEmergencyStop();
    void readHardwareInputs();
    bool canTransition(MaraMode from, MaraMode to);
};
