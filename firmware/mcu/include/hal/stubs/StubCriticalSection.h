// include/hal/stubs/StubCriticalSection.h
// Stub critical section implementation for native/test builds
#pragma once

#include "../ICriticalSection.h"

namespace hal {

class StubCriticalSection : public ICriticalSection {
public:
    void initSpinlock(SpinlockHandle& lock) override { (void)lock; }
    void enterCritical(SpinlockHandle& lock) override { (void)lock; }
    void exitCritical(SpinlockHandle& lock) override { (void)lock; }
    void enterCriticalISR(SpinlockHandle& lock) override { (void)lock; }
    void exitCriticalISR(SpinlockHandle& lock) override { (void)lock; }
};

} // namespace hal
