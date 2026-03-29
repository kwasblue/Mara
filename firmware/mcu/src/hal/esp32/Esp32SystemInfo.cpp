#include "hal/esp32/Esp32SystemInfo.h"
#include <esp_system.h>
#include <esp_chip_info.h>
#include <rom/rtc.h>
#include <Arduino.h>  // For getCpuFrequencyMhz()

namespace hal {

ResetReason Esp32SystemInfo::convertResetReason(int rawReason) {
    // ESP32 RESET_REASON enum values from rom/rtc.h
    switch (rawReason) {
        case 1:  // POWERON_RESET
            return ResetReason::PowerOn;
        case 3:  // SW_RESET (legacy)
        case 4:  // OWDT_RESET (legacy watchdog)
            return ResetReason::Software;
        case 5:  // DEEPSLEEP_RESET
            return ResetReason::DeepSleep;
        case 6:  // SDIO_RESET
            return ResetReason::Sdio;
        case 7:  // TG0WDT_SYS_RESET
        case 8:  // TG1WDT_SYS_RESET
        case 9:  // RTCWDT_SYS_RESET
        case 11: // TGWDT_CPU_RESET
        case 13: // RTCWDT_CPU_RESET
        case 15: // RTCWDT_BROWN_OUT_RESET
        case 17: // RTCWDT_RTC_RESET
            return ResetReason::Watchdog;
        case 10: // INTRUSION_RESET
            return ResetReason::External;
        case 12: // SW_CPU_RESET
            return ResetReason::Software;
        case 14: // EXT_CPU_RESET
            return ResetReason::External;
        case 16: // MAIN_POWER_RESET (brownout)
            return ResetReason::Brownout;
        default:
            return ResetReason::Unknown;
    }
}

ResetReason Esp32SystemInfo::getResetReason() {
    return getResetReason(0);
}

ResetReason Esp32SystemInfo::getResetReason(uint8_t core) {
    int raw = rtc_get_reset_reason(core);
    return convertResetReason(raw);
}

uint8_t Esp32SystemInfo::getResetReasonRaw(uint8_t core) {
    return static_cast<uint8_t>(rtc_get_reset_reason(core));
}

const char* Esp32SystemInfo::getChipModel() {
    esp_chip_info_t info;
    esp_chip_info(&info);

    switch (info.model) {
        case CHIP_ESP32:
            return "ESP32";
        case CHIP_ESP32S2:
            return "ESP32-S2";
        case CHIP_ESP32S3:
            return "ESP32-S3";
        case CHIP_ESP32C3:
            return "ESP32-C3";
        case CHIP_ESP32H2:
            return "ESP32-H2";
        default:
            return "ESP32-Unknown";
    }
}

uint8_t Esp32SystemInfo::getChipRevision() {
    esp_chip_info_t info;
    esp_chip_info(&info);
    return info.revision;
}

uint8_t Esp32SystemInfo::getCoreCount() {
    esp_chip_info_t info;
    esp_chip_info(&info);
    return info.cores;
}

uint32_t Esp32SystemInfo::getCpuFreqMHz() {
    return getCpuFrequencyMhz();  // Arduino ESP32 helper function
}

size_t Esp32SystemInfo::getChipId(uint8_t* id, size_t maxLen) {
    if (id == nullptr || maxLen == 0) {
        return 0;
    }

    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);

    size_t copyLen = maxLen < 6 ? maxLen : 6;
    for (size_t i = 0; i < copyLen; ++i) {
        id[i] = mac[i];
    }

    return copyLen;
}

} // namespace hal
