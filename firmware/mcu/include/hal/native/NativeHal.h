// include/hal/native/NativeHal.h
// Native HAL implementation for unit testing and host-side builds.
// Provides stub implementations of all HAL interfaces.
#pragma once

#include "config/FeatureFlags.h"
#include "NativeClock.h"
#include "NativeLogger.h"
#include "NativeTaskScheduler.h"
#include "NativeTransportFactory.h"
#include "../Hal.h"

// Stub implementations for interfaces not yet implemented
#include "../stubs/StubGpio.h"
#include "../stubs/StubPwm.h"
#include "../stubs/StubServo.h"
#include "../stubs/StubI2c.h"
#include "../stubs/StubTimer.h"
#include "../stubs/StubWatchdog.h"
#include "../stubs/StubCriticalSection.h"
#include "../stubs/StubPersistence.h"
#include "../stubs/StubSystemInfo.h"

namespace hal {

/// Native HAL storage - owns all HAL instances for test/native builds
struct NativeHalStorage {
    // Core timing
    NativeClock    clock;

    // Stub implementations for hardware interfaces
    StubGpio       gpio;
    StubPwm        pwm;
    StubServo      servo;
    StubI2c        i2c;
    StubI2c        i2c1;
    StubTimer      timer;
    StubWatchdog   watchdog;

    // System HAL components
    StubCriticalSection critical;
    StubPersistence     persistence;
    StubSystemInfo      systemInfo;
    NativeTaskScheduler scheduler;
    NativeLogger        logger;
    NativeTransportFactory transportFactory;

    /// Build HalContext with pointers to owned instances
    HalContext buildContext() {
        return HalContext{
            .clock       = &clock,
            .gpio        = &gpio,
            .pwm         = &pwm,
            .servo       = &servo,
            .i2c         = &i2c,
            .i2c1        = &i2c1,
            .timer       = &timer,
            .watchdog    = &watchdog,
            .can         = nullptr,  // No CAN on native
            .critical    = &critical,
            .heapMonitor = nullptr,  // No heap monitor on native
            .i2sAudio    = nullptr,  // No audio on native
            .persistence = &persistence,
            .systemInfo  = &systemInfo,
            .scheduler   = &scheduler,
            .logger      = &logger,
            .transportFactory = &transportFactory,
            .ota         = nullptr,  // No OTA on native
            .wifi        = nullptr   // No WiFi on native
        };
    }
};

} // namespace hal
