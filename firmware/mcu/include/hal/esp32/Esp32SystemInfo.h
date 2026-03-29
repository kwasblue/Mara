#pragma once

#include "../ISystemInfo.h"

namespace hal {

/// ESP32 system info implementation using ESP-IDF APIs
class Esp32SystemInfo : public ISystemInfo {
public:
    Esp32SystemInfo() = default;
    ~Esp32SystemInfo() = default;

    ResetReason getResetReason() override;
    ResetReason getResetReason(uint8_t core) override;
    uint8_t getResetReasonRaw(uint8_t core = 0) override;

    const char* getChipModel() override;
    uint8_t getChipRevision() override;
    uint8_t getCoreCount() override;
    uint32_t getCpuFreqMHz() override;
    size_t getChipId(uint8_t* id, size_t maxLen) override;

private:
    /// Convert ESP32 raw reset reason to HAL enum
    static ResetReason convertResetReason(int rawReason);
};

} // namespace hal
