#pragma once

#include <cstdint>
#include <cstddef>

namespace hal {

/// Reset reason codes (platform-agnostic subset)
enum class ResetReason : uint8_t {
    Unknown = 0,
    PowerOn = 1,        // Power-on reset
    External = 2,       // External reset (reset pin)
    Software = 3,       // Software reset (esp_restart, NVIC_SystemReset)
    Panic = 4,          // Software panic/exception
    Watchdog = 5,       // Watchdog timer reset
    DeepSleep = 6,      // Wake from deep sleep
    Brownout = 7,       // Brownout reset (low voltage)
    Sdio = 8,           // SDIO reset (ESP32-specific)
    Usb = 9,            // USB reset
    Jtag = 10           // JTAG reset
};

/// Abstract system info interface for platform portability
/// Provides reset reason and other system-level information.
///
/// Usage:
///   ISystemInfo* sysInfo = hal.systemInfo;
///   ResetReason reason = sysInfo->getResetReason();
///   uint8_t rawReason = sysInfo->getResetReasonRaw();
///
/// Notes:
///   - getResetReason() returns platform-agnostic enum
///   - getResetReasonRaw() returns raw platform value for debugging
///   - On multi-core systems, getResetReason(core) can query per-core reason
class ISystemInfo {
public:
    virtual ~ISystemInfo() = default;

    /// Get reset reason for the primary core (core 0)
    /// @return Platform-agnostic reset reason
    virtual ResetReason getResetReason() = 0;

    /// Get reset reason for a specific core
    /// @param core Core number (0 on single-core, 0-1 on dual-core)
    /// @return Platform-agnostic reset reason
    virtual ResetReason getResetReason(uint8_t core) = 0;

    /// Get raw platform-specific reset reason value
    /// Useful for debugging platform-specific issues
    /// @param core Core number (default 0)
    /// @return Raw reset reason code (platform-specific)
    virtual uint8_t getResetReasonRaw(uint8_t core = 0) = 0;

    /// Get chip/MCU model string
    /// @return Chip model (e.g., "ESP32-D0WDQ6", "STM32F411CEU6")
    virtual const char* getChipModel() = 0;

    /// Get chip revision
    /// @return Revision number
    virtual uint8_t getChipRevision() = 0;

    /// Get number of CPU cores
    /// @return Number of cores (1 or 2 typically)
    virtual uint8_t getCoreCount() = 0;

    /// Get CPU frequency in MHz
    /// @return CPU frequency
    virtual uint32_t getCpuFreqMHz() = 0;

    /// Get unique chip ID (MAC address or similar)
    /// @param id Output buffer (at least 6 bytes for MAC)
    /// @param maxLen Buffer size
    /// @return Number of bytes written
    virtual size_t getChipId(uint8_t* id, size_t maxLen) = 0;
};

} // namespace hal
