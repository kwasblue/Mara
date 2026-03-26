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
    void activate();
    void deactivate();
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
    
    // Validation
    bool validateVelocity(float vx, float omega, float& out_vx, float& out_omega);
    
    // Callback
    void onStop(StopCallback cb) { stopCallback_ = cb; }

    // Emergency stop callback - called in addition to stopCallback for critical stops
    // This should directly disable motor PWM, not go through motion controller
    void onEmergencyStop(StopCallback cb) { emergencyStopCallback_ = cb; }

    // Clock injection for testability
    void setClock(mara::IClock* clk) { clock_ = clk; }

    /// Set HAL GPIO driver (for E-stop, bypass, relay pins)
    void setHalGpio(hal::IGpio* gpio) { halGpio_ = gpio; }

    /// Set HAL watchdog driver
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
    bool wasMoving_ = false;  // True if non-zero velocity was commanded
    bool stopLatched_ = false;  // Prevent repeated stop callback spam for one fault episode

    StopCallback stopCallback_;
    StopCallback emergencyStopCallback_;  // Direct motor disable for E-stop
    mara::IClock* clock_ = nullptr;

    /// Get current time from clock or fallback to system clock
    uint32_t now_ms() const {
        if (clock_) return clock_->millis();
        return mara::getSystemClock().millis();
    }

    mara::SpinlockType lock_ = MCU_SPINLOCK_INIT;

    void triggerStop();
    void triggerEmergencyStop();  // Direct motor disable
    void readHardwareInputs();
    bool canTransition(MaraMode from, MaraMode to);

};

// Helper to convert mode to string
// inline const char* maraModeToString(MaraMode m) {
//     switch (m) {
//         case MaraMode::BOOT: return "BOOT";
//         case MaraMode::DISCONNECTED: return "DISCONNECTED";
//         case MaraMode::IDLE: return "IDLE";
//         case MaraMode::ARMED: return "ARMED";
//         case MaraMode::ACTIVE: return "ACTIVE";
//         case MaraMode::ESTOPPED: return "ESTOPPED";
//         default: return "UNKNOWN";
//     }
// }       