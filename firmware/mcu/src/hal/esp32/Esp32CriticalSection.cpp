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

void Esp32CriticalSection::enterCriticalISR(SpinlockHandle& lock) {
    portENTER_CRITICAL_ISR(getMux(lock));
}

void Esp32CriticalSection::exitCriticalISR(SpinlockHandle& lock) {
    portEXIT_CRITICAL_ISR(getMux(lock));
}

} // namespace hal
