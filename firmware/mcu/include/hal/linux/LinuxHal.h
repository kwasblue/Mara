// include/hal/linux/LinuxHal.h
// Linux HAL - Hardware Abstraction Layer for Linux robots
//
// Enables MARA firmware to run natively on Linux SBCs (Raspberry Pi, Jetson, etc.)
// Provides the same HAL interface as ESP32 but implemented with Linux APIs.
#pragma once

#include "config/FeatureFlags.h"
#include "LinuxClock.h"
#include "LinuxGpio.h"
#include "LinuxI2c.h"
#include "LinuxPwm.h"
#include "LinuxServo.h"
#include "LinuxTimer.h"
#include "LinuxTaskScheduler.h"
#include "LinuxCriticalSection.h"
#include "LinuxLogger.h"
#include "LinuxPersistence.h"
#include "LinuxSystemInfo.h"
#include "LinuxTransportFactory.h"
#include "../Hal.h"

// Stubs for interfaces not implemented on Linux
#include "../stubs/StubWatchdog.h"

namespace hal {

/// Linux HAL storage - owns all HAL instances for Linux builds
///
/// This struct provides the same interface as Esp32HalStorage and
/// NativeHalStorage, allowing the MARA firmware core to be
/// platform-agnostic.
///
/// Usage:
///   LinuxHalStorage hal;
///   HalContext ctx = hal.buildContext();
///   ctx.clock->millis();
///   ctx.gpio->pinMode(17, PinMode::Output);
///
/// Hardware support on Linux:
/// - GPIO via libgpiod (/dev/gpiochip*)
/// - I2C via i2c-dev (/dev/i2c-*)
/// - PWM via sysfs (/sys/class/pwm/)
/// - Servos via PWM or PCA9685 I2C driver
/// - Timers via timerfd
/// - Tasks via pthreads with optional SCHED_FIFO
struct LinuxHalStorage {
    // Core timing
    LinuxClock clock;

    // Hardware interfaces
    LinuxGpio gpio;
    LinuxPwm pwm;
    LinuxServo servo;
    LinuxI2c i2c{1};       // Primary I2C bus (/dev/i2c-1)
    LinuxI2c i2c1{0};      // Secondary I2C bus (/dev/i2c-0)
    LinuxTimer timer;

    // Stub for watchdog (Linux uses systemd watchdog instead)
    StubWatchdog watchdog;

    // System HAL components
    LinuxCriticalSection critical;
    LinuxPersistence persistence;
    LinuxSystemInfo systemInfo;
    LinuxTaskScheduler scheduler;
    LinuxLogger logger;
    LinuxTransportFactory transportFactory;

    /// Build HalContext with pointers to owned instances
    ///
    /// Returns a context struct that can be passed to firmware modules.
    /// All pointers remain valid for the lifetime of this LinuxHalStorage.
    HalContext buildContext() {
        // Initialize servo with PWM backend
        servo = LinuxServo(&pwm);

        return HalContext{
            .clock       = &clock,
            .gpio        = &gpio,
            .pwm         = &pwm,
            .servo       = &servo,
            .i2c         = &i2c,
            .i2c1        = &i2c1,
            .timer       = &timer,
            .watchdog    = &watchdog,
            .can         = nullptr,       // No CAN support yet
            .critical    = &critical,
            .heapMonitor = nullptr,       // Use /proc/self/status instead
            .i2sAudio    = nullptr,       // No I2S audio yet
            .persistence = &persistence,
            .systemInfo  = &systemInfo,
            .scheduler   = &scheduler,
            .logger      = &logger,
            .transportFactory = &transportFactory,
            .ota         = nullptr,       // No OTA (use package manager)
            .wifi        = nullptr        // WiFi via Python/NetworkManager
        };
    }

    /// Initialize all hardware interfaces
    ///
    /// Call this before using the HAL. On Linux, this:
    /// - Opens GPIO chip
    /// - Initializes I2C buses
    /// - Sets up timers
    ///
    /// @return true if all initialization succeeded
    bool begin() {
        bool ok = true;
        ok &= gpio.begin();
        ok &= i2c.begin(0, 0);   // Linux ignores SDA/SCL pins
        ok &= i2c1.begin(0, 0);
        ok &= pwm.begin();
        return ok;
    }

    /// Clean up hardware interfaces
    void end() {
        gpio.end();
        i2c.end();
        i2c1.end();
        pwm.end();
    }
};

} // namespace hal
