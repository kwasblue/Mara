// include/hal/stubs/StubSystemInfo.h
// Stub system info implementation for native/test builds
#pragma once

#include "../ISystemInfo.h"
#include <cstring>

namespace hal {

class StubSystemInfo : public ISystemInfo {
public:
    ResetReason getResetReason() override { return ResetReason::PowerOn; }
    ResetReason getResetReason(uint8_t core) override { (void)core; return ResetReason::PowerOn; }
    uint8_t getResetReasonRaw(uint8_t core = 0) override { (void)core; return 1; }

    const char* getChipModel() override { return "Native-Stub"; }
    uint8_t getChipRevision() override { return 0; }
    uint8_t getCoreCount() override { return 1; }
    uint32_t getCpuFreqMHz() override { return 0; }

    size_t getChipId(uint8_t* id, size_t maxLen) override {
        if (maxLen >= 6) {
            std::memset(id, 0, 6);
            return 6;
        }
        return 0;
    }
};

} // namespace hal
