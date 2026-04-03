#include "hal/esp32/Esp32CriticalSection.h"
#include <cstring>

namespace hal {

portMUX_TYPE* Esp32CriticalSection::getMux(SpinlockHandle& lock) {
    // SpinlockHandle::storage is sized to hold portMUX_TYPE
    static_assert(sizeof(portMUX_TYPE) <= sizeof(SpinlockHandle::storage),
                  "SpinlockHandle storage too small for portMUX_TYPE");
    return reinterpret_cast<portMUX_TYPE*>(lock.storage);
}

void Esp32CriticalSection::initSpinlock(SpinlockHandle& lock) {
    portMUX_TYPE* mux = getMux(lock);
    // Initialize to unlocked state
    portMUX_TYPE init = portMUX_INITIALIZER_UNLOCKED;
    std::memcpy(mux, &init, sizeof(portMUX_TYPE));
}

void Esp32CriticalSection::enterCritical(SpinlockHandle& lock) {
    portENTER_CRITICAL(getMux(lock));
}

void Esp32CriticalSection::exitCritical(SpinlockHandle& lock) {
    portEXIT_CRITICAL(getMux(lock));
}

// NOTE: ISR variants are currently unused in the codebase. All ISR handlers
// (e.g., EncoderManager::handleA/B) use single-word volatile writes which are
// atomic on ESP32. These methods are provided for future use if an ISR needs
// to access shared state larger than a single aligned word.
void Esp32CriticalSection::enterCriticalISR(SpinlockHandle& lock) {
    portENTER_CRITICAL_ISR(getMux(lock));
}

void Esp32CriticalSection::exitCriticalISR(SpinlockHandle& lock) {
    portEXIT_CRITICAL_ISR(getMux(lock));
}

} // namespace hal
