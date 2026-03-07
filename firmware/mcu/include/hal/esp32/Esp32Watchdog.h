#pragma once

#include "../IWatchdog.h"

namespace hal {

/// ESP32 Task Watchdog Timer implementation
class Esp32Watchdog : public IWatchdog {
public:
    bool begin(uint32_t timeoutSeconds, bool panicOnTimeout = true) override;
    bool addCurrentTask() override;
    bool removeCurrentTask() override;
    void reset() override;
    bool isEnabled() const override { return enabled_; }

private:
    bool enabled_ = false;
};

} // namespace hal
