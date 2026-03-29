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
#include "Esp32CriticalSection.h"
#include "Esp32HeapMonitor.h"
#include "Esp32I2sAudio.h"
#include "Esp32Persistence.h"
#include "Esp32SystemInfo.h"
#include "Esp32TaskScheduler.h"
#include "Esp32Logger.h"
#include "Esp32TransportFactory.h"
#include "Esp32Ota.h"
#include "Esp32WifiManager.h"
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

    // New HAL components for portability
    Esp32CriticalSection critical;
    Esp32HeapMonitor     heapMonitor;
#if HAS_AUDIO
    Esp32I2sAudio        i2sAudio;
#endif
    Esp32Persistence     persistence;
    Esp32SystemInfo      systemInfo;
    Esp32TaskScheduler   scheduler;
    Esp32Logger          logger;
    Esp32TransportFactory transportFactory;
#if HAS_OTA
    Esp32Ota             ota;
#endif
#if HAS_WIFI
    Esp32WifiManager     wifiManager;
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
            .can      = &can,
#else
            .can      = nullptr,
#endif
            .critical    = &critical,
            .heapMonitor = &heapMonitor,
#if HAS_AUDIO
            .i2sAudio    = &i2sAudio,
#else
            .i2sAudio    = nullptr,
#endif
            .persistence = &persistence,
            .systemInfo  = &systemInfo,
            .scheduler   = &scheduler,
            .logger      = &logger,
            .transportFactory = &transportFactory,
#if HAS_OTA
            .ota         = &ota,
#else
            .ota         = nullptr,
#endif
#if HAS_WIFI
            .wifi        = &wifiManager
#else
            .wifi        = nullptr
#endif
        };
    }
};

} // namespace hal
