#pragma once

#include <cstdint>
#include <cstddef>

namespace hal {

/// Memory capability flags for heap queries
enum class MemoryCaps : uint32_t {
    Default = 0,        // Default memory (any type)
    Internal = 1,       // Internal SRAM
    External = 2,       // External SPI RAM (PSRAM)
    DMA = 4,            // DMA-capable memory
    Exec = 8            // Executable memory (for code)
};

/// Abstract heap monitor interface for platform portability
/// Provides heap size queries for real-time debug checks.
///
/// Usage (in RT_CONTROL_ENTER/EXIT macros):
///   size_t before = hal.heapMonitor->getFreeSize(MemoryCaps::Default);
///   // ... RT code ...
///   size_t after = hal.heapMonitor->getFreeSize(MemoryCaps::Default);
///   if (after < before - threshold) { /* allocation detected */ }
///
/// Note: This interface is optional (nullptr if not available).
class IHeapMonitor {
public:
    virtual ~IHeapMonitor() = default;

    /// Get free heap size with specified capabilities
    /// @param caps Memory capability filter
    /// @return Free bytes matching the capability filter
    virtual size_t getFreeSize(MemoryCaps caps = MemoryCaps::Default) = 0;

    /// Get largest free contiguous block
    /// @param caps Memory capability filter
    /// @return Size of largest free block in bytes
    virtual size_t getLargestFreeBlock(MemoryCaps caps = MemoryCaps::Default) = 0;

    /// Get minimum free heap size since boot (watermark)
    /// @param caps Memory capability filter
    /// @return Minimum free bytes observed
    virtual size_t getMinFreeSize(MemoryCaps caps = MemoryCaps::Default) = 0;

    /// Get total heap size with specified capabilities
    /// @param caps Memory capability filter
    /// @return Total heap size in bytes
    virtual size_t getTotalSize(MemoryCaps caps = MemoryCaps::Default) = 0;
};

} // namespace hal
