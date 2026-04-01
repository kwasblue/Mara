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
#include "IServo.h"
#include "II2c.h"
#include "ITimer.h"
#include "IWatchdog.h"
#include "ICan.h"
#include "ICriticalSection.h"
#include "IHeapMonitor.h"
#include "II2sAudio.h"
#include "IPersistence.h"
#include "ISystemInfo.h"
#include "ITaskScheduler.h"
#include "ILogger.h"
#include "ITransportFactory.h"
#include "IOta.h"
#include "IWifiManager.h"

namespace hal {

/// HAL context - provides access to all hardware interfaces
struct HalContext {
    IGpio*     gpio     = nullptr;
    IPwm*      pwm      = nullptr;
    IServo*    servo    = nullptr;   // Servo motors (optional, HAS_SERVO)
    II2c*      i2c      = nullptr;   // Primary I2C bus
    II2c*      i2c1     = nullptr;   // Secondary I2C bus (optional)
    ITimer*    timer    = nullptr;
    IWatchdog* watchdog = nullptr;
    ICan*      can      = nullptr;   // CAN bus (optional)

    // New interfaces for portability
    ICriticalSection* critical    = nullptr;
    IHeapMonitor*     heapMonitor = nullptr;  // Optional (debug)
    II2sAudio*        i2sAudio    = nullptr;  // Optional (HAS_AUDIO)
    IPersistence*     persistence = nullptr;
    ISystemInfo*      systemInfo  = nullptr;
    ITaskScheduler*   scheduler   = nullptr;
    ILogger*          logger      = nullptr;  // Logging abstraction
    ITransportFactory* transportFactory = nullptr;  // Transport creation
    IOta*             ota         = nullptr;  // OTA updates
    IWifiManager*     wifi        = nullptr;  // WiFi management
};

} // namespace hal
