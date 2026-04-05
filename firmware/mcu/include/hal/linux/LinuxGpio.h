// include/hal/linux/LinuxGpio.h
// Linux GPIO implementation using libgpiod v2 API
//
// Requires: libgpiod-dev (apt install libgpiod-dev)
// For Raspberry Pi, Jetson, and other Linux SBCs with GPIO support.
#pragma once

#include "../IGpio.h"
#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <thread>
#include <atomic>

// Forward declarations for libgpiod types
// Actual inclusion happens in the .cpp file
struct gpiod_chip;
struct gpiod_line_request;

namespace hal {

/// Linux GPIO implementation using libgpiod v2
///
/// Provides GPIO access via /dev/gpiochip* interface.
/// Supports input, output, and interrupt modes.
///
/// Note: Requires root or gpio group membership for access.
class LinuxGpio : public IGpio {
public:
    /// Constructor
    /// @param chipPath Path to GPIO chip (default: /dev/gpiochip0)
    explicit LinuxGpio(const char* chipPath = "/dev/gpiochip0");

    ~LinuxGpio();

    void pinMode(uint8_t pin, PinMode mode) override;
    void digitalWrite(uint8_t pin, uint8_t value) override;
    int digitalRead(uint8_t pin) override;
    void toggle(uint8_t pin) override;
    void attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) override;
    void detachInterrupt(uint8_t pin) override;
    void disableInterrupts() override;
    void enableInterrupts() override;

    /// Initialize the GPIO chip
    /// @return true if successful
    bool begin();

    /// Close the GPIO chip
    void end();

private:
    struct PinState {
        PinMode mode = PinMode::Input;
        uint8_t value = 0;
        gpiod_line_request* request = nullptr;
        void (*isr)() = nullptr;
        InterruptMode intMode = InterruptMode::Disabled;
        std::thread* intThread = nullptr;
        std::atomic<bool> intRunning{false};
    };

    gpiod_chip* chip_ = nullptr;
    char chipPath_[64];
    std::map<uint8_t, PinState> pins_;
    std::mutex mutex_;
    std::atomic<bool> interruptsEnabled_{true};

    void releaseLine(uint8_t pin);
    bool requestLine(uint8_t pin, PinMode mode);
    void interruptHandler(uint8_t pin);
};

} // namespace hal
