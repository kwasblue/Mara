#pragma once

#include "../ICriticalSection.h"
#include <freertos/FreeRTOS.h>
#include <freertos/portmacro.h>

namespace hal {

/// ESP32 critical section implementation using FreeRTOS spinlocks
class Esp32CriticalSection : public ICriticalSection {
public:
    Esp32CriticalSection() = default;
    ~Esp32CriticalSection() = default;

    void initSpinlock(SpinlockHandle& lock) override;
    void enterCritical(SpinlockHandle& lock) override;
    void exitCritical(SpinlockHandle& lock) override;
    void enterCriticalISR(SpinlockHandle& lock) override;
    void exitCriticalISR(SpinlockHandle& lock) override;

private:
    /// Get the portMUX_TYPE pointer from our handle
    static portMUX_TYPE* getMux(SpinlockHandle& lock);
};

} // namespace hal
