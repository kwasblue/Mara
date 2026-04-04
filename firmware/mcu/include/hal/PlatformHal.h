// include/hal/PlatformHal.h
// =============================================================================
// SINGLE CONFIGURATION POINT FOR TARGET PLATFORM HAL
// =============================================================================
//
// This file is the ONE PLACE where platform selection cascades to the HAL.
// Include this instead of platform-specific HAL headers.
//
// The platform is detected automatically from PlatformConfig.h based on
// compiler defines. To change target platforms:
//
//   1. PlatformIO: Change [env] in platformio.ini
//   2. CMake: Set -DPLATFORM_xxx=1
//   3. Make: Set PLATFORM=xxx
//
// The build system sets the appropriate defines, and this file selects
// the correct HAL implementation automatically.
//
// Usage:
//   #include "hal/PlatformHal.h"
//
//   hal::PlatformHalStorage hal;   // Correct type for current platform
//   hal::HalContext ctx = hal.buildContext();
//
#pragma once

#include "config/PlatformConfig.h"
#include "hal/Hal.h"

// =============================================================================
// PLATFORM-SPECIFIC HAL INCLUDES
// =============================================================================
// Each platform provides a HalStorage struct with the same interface:
//   - Member instances of all HAL components
//   - HalContext buildContext() method
//
// The struct is typedef'd to PlatformHalStorage for uniform usage.

#if PLATFORM_ESP32
    #include "hal/esp32/Esp32Hal.h"
    namespace hal {
        using PlatformHalStorage = Esp32HalStorage;
    }

#elif PLATFORM_STM32
    // STM32 HAL - requires implementation in hal/stm32/
    #include "hal/stm32/Stm32Hal.h"
    namespace hal {
        using PlatformHalStorage = Stm32HalStorage;
    }

#elif PLATFORM_RP2040
    // RP2040 HAL - requires implementation in hal/rp2040/
    #include "hal/rp2040/Rp2040Hal.h"
    namespace hal {
        using PlatformHalStorage = Rp2040HalStorage;
    }

#elif PLATFORM_NATIVE
    // Native/test HAL - stubs for unit testing
    #include "hal/native/NativeHal.h"
    namespace hal {
        using PlatformHalStorage = NativeHalStorage;
    }

#else
    #error "No HAL implementation for current platform. Check PlatformConfig.h"
#endif

// =============================================================================
// CONVENIENCE MACROS
// =============================================================================

// Check if current platform has a specific HAL feature
// Usage: #if HAL_HAS_WIFI ... #endif
#define HAL_HAS_WIFI    (PLATFORM_HAS_WIFI_CAPABLE && HAS_WIFI)
#define HAL_HAS_BLE     (PLATFORM_HAS_BLE_CAPABLE && HAS_BLE)
#define HAL_HAS_CAN     (PLATFORM_HAS_CAN_CAPABLE && HAS_CAN)
#define HAL_HAS_OTA     (PLATFORM_ESP32 && HAS_OTA)  // OTA currently ESP32 only
