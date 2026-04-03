#include "hal/esp32/Esp32HeapMonitor.h"
#include <esp_heap_caps.h>

namespace hal {

// NOTE: MemoryCaps enum values map one-to-one to MALLOC_CAP_* flags.
// This design doesn't support combining flags (e.g., Internal | DMA).
// To query DMA-capable internal memory, callers would need a new enum value
// or direct access to heap_caps_* with raw uint32_t flags. For typical use
// (monitoring heap by region), single-cap queries are sufficient.
uint32_t Esp32HeapMonitor::toEspCaps(MemoryCaps caps) {
    switch (caps) {
        case MemoryCaps::Internal:
            return MALLOC_CAP_INTERNAL;
        case MemoryCaps::External:
            return MALLOC_CAP_SPIRAM;
        case MemoryCaps::DMA:
            return MALLOC_CAP_DMA;
        case MemoryCaps::Exec:
            return MALLOC_CAP_EXEC;
        case MemoryCaps::Default:
        default:
            return MALLOC_CAP_DEFAULT;
    }
}

size_t Esp32HeapMonitor::getFreeSize(MemoryCaps caps) {
    return heap_caps_get_free_size(toEspCaps(caps));
}

size_t Esp32HeapMonitor::getLargestFreeBlock(MemoryCaps caps) {
    return heap_caps_get_largest_free_block(toEspCaps(caps));
}

size_t Esp32HeapMonitor::getMinFreeSize(MemoryCaps caps) {
    return heap_caps_get_minimum_free_size(toEspCaps(caps));
}

size_t Esp32HeapMonitor::getTotalSize(MemoryCaps caps) {
    return heap_caps_get_total_size(toEspCaps(caps));
}

} // namespace hal
