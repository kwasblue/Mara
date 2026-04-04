// include/hal/stubs/StubWatchdog.h
// Stub watchdog implementation for native/test builds
#pragma once

#include "../IWatchdog.h"

namespace hal {

class StubWatchdog : public IWatchdog {
public:
    bool begin(uint32_t timeoutSeconds, bool panicOnTimeout = true) override {
        (void)timeoutSeconds; (void)panicOnTimeout;
        enabled_ = true;
        return true;
    }

    bool addCurrentTask() override { return true; }
    bool removeCurrentTask() override { return true; }
    void reset() override {}
    bool isEnabled() const override { return enabled_; }

private:
    bool enabled_ = false;
};

} // namespace hal
