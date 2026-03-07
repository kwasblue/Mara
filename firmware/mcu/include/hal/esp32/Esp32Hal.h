#pragma once

// ESP32 HAL Implementation
// Include this header for ESP32-specific HAL classes

#include "config/FeatureFlags.h"
#include "Esp32Gpio.h"
#include "Esp32Pwm.h"
#include "Esp32I2c.h"
#include "Esp32Timer.h"
#include "Esp32Watchdog.h"
#include "Esp32Can.h"
#include "../Hal.h"

namespace hal {

/// ESP32 HAL storage - owns all HAL instances
struct Esp32HalStorage {
    Esp32Gpio     gpio;
    Esp32Pwm      pwm;
    Esp32I2c      i2c{0};   // Wire (primary)
    Esp32I2c      i2c1{1};  // Wire1 (secondary)
    Esp32Timer    timer;
    Esp32Watchdog watchdog;
#if HAS_CAN
    Esp32Can      can;      // CAN bus (TWAI)
#endif

    /// Build HalContext with pointers to owned instances
    HalContext buildContext() {
        return HalContext{
            .gpio     = &gpio,
            .pwm      = &pwm,
            .i2c      = &i2c,
            .i2c1     = &i2c1,
            .timer    = &timer,
            .watchdog = &watchdog,
#if HAS_CAN
            .can      = &can
#else
            .can      = nullptr
#endif
        };
    }
};

} // namespace hal
