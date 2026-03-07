#pragma once

// Hardware Abstraction Layer (HAL) - Platform-agnostic interfaces
//
// Usage:
//   #include <hal/Hal.h>
//
// For platform-specific implementations, see:
//   - src/hal/esp32/   (ESP32/ESP32-S2/ESP32-S3)
//   - src/hal/stm32/   (STM32 family) [future]
//   - src/hal/rp2040/  (Raspberry Pi Pico) [future]

#include "IGpio.h"
#include "IPwm.h"
#include "II2c.h"
#include "ITimer.h"
#include "IWatchdog.h"
#include "ICan.h"

namespace hal {

/// HAL context - provides access to all hardware interfaces
struct HalContext {
    IGpio*     gpio     = nullptr;
    IPwm*      pwm      = nullptr;
    II2c*      i2c      = nullptr;   // Primary I2C bus
    II2c*      i2c1     = nullptr;   // Secondary I2C bus (optional)
    ITimer*    timer    = nullptr;
    IWatchdog* watchdog = nullptr;
    ICan*      can      = nullptr;   // CAN bus (optional)
};

} // namespace hal
