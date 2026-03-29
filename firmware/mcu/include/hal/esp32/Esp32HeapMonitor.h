#pragma once

#include "../IHeapMonitor.h"

namespace hal {

/// ESP32 heap monitor implementation using ESP-IDF heap_caps API
class Esp32HeapMonitor : public IHeapMonitor {
public:
    Esp32HeapMonitor() = default;
    ~Esp32HeapMonitor() = default;

    size_t getFreeSize(MemoryCaps caps = MemoryCaps::Default) override;
    size_t getLargestFreeBlock(MemoryCaps caps = MemoryCaps::Default) override;
    size_t getMinFreeSize(MemoryCaps caps = MemoryCaps::Default) override;
    size_t getTotalSize(MemoryCaps caps = MemoryCaps::Default) override;

private:
    /// Convert HAL MemoryCaps to ESP-IDF caps flags
    static uint32_t toEspCaps(MemoryCaps caps);
};

} // namespace hal
