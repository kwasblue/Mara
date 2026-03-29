// include/config/PlatformConfig.h
// Centralized platform detection and capability macros.
// This file should be included FIRST in any source that needs platform detection.
// It replaces scattered #ifdef ARDUINO, #ifdef ESP32 patterns.
#pragma once

// =============================================================================
// PLATFORM DETECTION
// =============================================================================
// These are automatically detected based on compiler/build system defines.
// Only ONE platform should be active at a time.

#if defined(ESP32) || defined(ARDUINO_ARCH_ESP32)
    #define PLATFORM_ESP32 1
    #define PLATFORM_NAME "esp32"
#elif defined(STM32F4) || defined(STM32F7) || defined(STM32H7) || defined(ARDUINO_ARCH_STM32)
    #define PLATFORM_STM32 1
    #define PLATFORM_NAME "stm32"
#elif defined(ARDUINO_ARCH_RP2040) || defined(PICO_BUILD)
    #define PLATFORM_RP2040 1
    #define PLATFORM_NAME "rp2040"
#elif defined(NATIVE_BUILD) || defined(UNIT_TEST) || !defined(ARDUINO)
    #define PLATFORM_NATIVE 1
    #define PLATFORM_NAME "native"
#else
    // Default to native for unknown platforms (unit tests, etc.)
    #define PLATFORM_NATIVE 1
    #define PLATFORM_NAME "native"
#endif

// Ensure mutually exclusive
#ifndef PLATFORM_ESP32
    #define PLATFORM_ESP32 0
#endif
#ifndef PLATFORM_STM32
    #define PLATFORM_STM32 0
#endif
#ifndef PLATFORM_RP2040
    #define PLATFORM_RP2040 0
#endif
#ifndef PLATFORM_NATIVE
    #define PLATFORM_NATIVE 0
#endif

// =============================================================================
// ARDUINO FRAMEWORK DETECTION
// =============================================================================
// Detect if Arduino framework is available (vs bare-metal or native)

#if defined(ARDUINO)
    #define PLATFORM_HAS_ARDUINO 1
#else
    #define PLATFORM_HAS_ARDUINO 0
#endif

// =============================================================================
// RTOS CAPABILITIES
// =============================================================================
// FreeRTOS is standard on ESP32, optional elsewhere

#if PLATFORM_ESP32
    #define HAS_FREERTOS 1
#elif PLATFORM_STM32
    // STM32 can have FreeRTOS, detected via build flag
    #ifndef HAS_FREERTOS
        #define HAS_FREERTOS 0
    #endif
#elif PLATFORM_RP2040
    // RP2040 can have FreeRTOS or use Pico SDK multicore
    #ifndef HAS_FREERTOS
        #define HAS_FREERTOS 0
    #endif
#else
    #define HAS_FREERTOS 0
#endif

// =============================================================================
// HARDWARE CAPABILITIES
// =============================================================================
// These indicate what hardware features the platform supports.
// Note: These indicate platform CAPABILITY, not whether the feature is ENABLED.
// Use FeatureFlags.h HAS_* macros to check if features are enabled.

#if PLATFORM_ESP32
    #define PLATFORM_HAS_WIFI_CAPABLE 1
    #define PLATFORM_HAS_BLE_CAPABLE 1
    #define PLATFORM_HAS_CAN_CAPABLE 1      // ESP32 has TWAI (CAN)
    #define PLATFORM_HAS_I2S_CAPABLE 1
    #define PLATFORM_HAS_DUAL_CORE 1
    #define PLATFORM_DEFAULT_SERIAL_BAUD 115200
#elif PLATFORM_STM32
    #define PLATFORM_HAS_WIFI_CAPABLE 0     // Requires external module
    #define PLATFORM_HAS_BLE_CAPABLE 0      // Requires external module
    #define PLATFORM_HAS_CAN_CAPABLE 1      // Most STM32 have CAN
    #define PLATFORM_HAS_I2S_CAPABLE 1
    #define PLATFORM_HAS_DUAL_CORE 0        // Most STM32 are single-core
    #define PLATFORM_DEFAULT_SERIAL_BAUD 115200
#elif PLATFORM_RP2040
    #define PLATFORM_HAS_WIFI_CAPABLE 0     // RP2040 base has no WiFi (Pico W does)
    #define PLATFORM_HAS_BLE_CAPABLE 0
    #define PLATFORM_HAS_CAN_CAPABLE 0      // No native CAN
    #define PLATFORM_HAS_I2S_CAPABLE 1      // PIO can do I2S
    #define PLATFORM_HAS_DUAL_CORE 1
    #define PLATFORM_DEFAULT_SERIAL_BAUD 115200
#else
    // Native/test build - no hardware capabilities
    #define PLATFORM_HAS_WIFI_CAPABLE 0
    #define PLATFORM_HAS_BLE_CAPABLE 0
    #define PLATFORM_HAS_CAN_CAPABLE 0
    #define PLATFORM_HAS_I2S_CAPABLE 0
    #define PLATFORM_HAS_DUAL_CORE 0
    #define PLATFORM_DEFAULT_SERIAL_BAUD 115200
#endif

// =============================================================================
// MEMORY CONSTRAINTS
// =============================================================================

#if PLATFORM_ESP32
    #define PLATFORM_RAM_KB 520             // ESP32 has ~520KB total SRAM
    #define PLATFORM_FLASH_KB 4096          // Typical 4MB flash
    #define PLATFORM_HAS_PSRAM_SUPPORT 1    // Some ESP32 modules have PSRAM
#elif PLATFORM_STM32
    #define PLATFORM_RAM_KB 128             // Varies widely, conservative default
    #define PLATFORM_FLASH_KB 512           // Varies widely
    #define PLATFORM_HAS_PSRAM_SUPPORT 0
#elif PLATFORM_RP2040
    #define PLATFORM_RAM_KB 264
    #define PLATFORM_FLASH_KB 2048          // Typical 2MB flash
    #define PLATFORM_HAS_PSRAM_SUPPORT 0
#else
    // Native - unlimited for practical purposes
    #define PLATFORM_RAM_KB 999999
    #define PLATFORM_FLASH_KB 999999
    #define PLATFORM_HAS_PSRAM_SUPPORT 0
#endif

// =============================================================================
// INCLUDE GUARDS FOR PLATFORM-SPECIFIC HEADERS
// =============================================================================
// Use these to conditionally include platform headers

#define PLATFORM_INCLUDE_ARDUINO    PLATFORM_HAS_ARDUINO
#define PLATFORM_INCLUDE_FREERTOS   HAS_FREERTOS
#define PLATFORM_INCLUDE_ESP32_HAL  PLATFORM_ESP32
#define PLATFORM_INCLUDE_STM32_HAL  PLATFORM_STM32
#define PLATFORM_INCLUDE_RP2040_SDK PLATFORM_RP2040

// =============================================================================
// HELPER MACROS FOR CONDITIONAL COMPILATION
// =============================================================================

// Use these instead of raw #ifdef ARDUINO or #ifdef ESP32

// PLATFORM_ONLY_ESP32 { code } - code only compiles on ESP32
#if PLATFORM_ESP32
    #define PLATFORM_ONLY_ESP32(code) code
#else
    #define PLATFORM_ONLY_ESP32(code)
#endif

// PLATFORM_ONLY_NATIVE { code } - code only compiles in native builds
#if PLATFORM_NATIVE
    #define PLATFORM_ONLY_NATIVE(code) code
#else
    #define PLATFORM_ONLY_NATIVE(code)
#endif

// PLATFORM_WHEN_ARDUINO { code } - code only compiles when Arduino framework present
#if PLATFORM_HAS_ARDUINO
    #define PLATFORM_WHEN_ARDUINO(code) code
#else
    #define PLATFORM_WHEN_ARDUINO(code)
#endif

// =============================================================================
// STATIC ASSERTIONS FOR SANITY
// =============================================================================
// Ensure exactly one platform is selected

static_assert(
    (PLATFORM_ESP32 + PLATFORM_STM32 + PLATFORM_RP2040 + PLATFORM_NATIVE) == 1,
    "Exactly one platform must be defined"
);
