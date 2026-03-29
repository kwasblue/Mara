#include "hal/esp32/Esp32HeapMonitor.h"
#include <esp_heap_caps.h>

namespace hal {

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
