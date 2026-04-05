// include/hal/linux/LinuxSystemInfo.h
// Linux system info implementation
//
// Reads system information from /proc/cpuinfo, /proc/meminfo, etc.
#pragma once

#include "../ISystemInfo.h"
#include <cstdint>
#include <cstring>

namespace hal {

/// Linux system info implementation
///
/// Provides system information from procfs and sysfs:
/// - CPU info from /proc/cpuinfo
/// - Memory info from /proc/meminfo
/// - Reset reason (always PowerOn on Linux)
/// - Unique ID from machine-id or CPU serial
class LinuxSystemInfo : public ISystemInfo {
public:
    LinuxSystemInfo();
    ~LinuxSystemInfo() = default;

    ResetReason getResetReason() override;
    ResetReason getResetReason(uint8_t core) override;
    uint8_t getResetReasonRaw(uint8_t core = 0) override;

    const char* getChipModel() override;
    uint8_t getChipRevision() override;
    uint8_t getCoreCount() override;
    uint32_t getCpuFreqMHz() override;
    size_t getChipId(uint8_t* id, size_t maxLen) override;

    /// Get total RAM in bytes
    uint64_t getTotalRam();

    /// Get available RAM in bytes
    uint64_t getAvailableRam();

    /// Get system uptime in seconds
    uint64_t getUptime();

    /// Get hostname
    const char* getHostname();

    /// Get kernel version
    const char* getKernelVersion();

private:
    char chipModel_[64] = {0};
    char hostname_[64] = {0};
    char kernelVersion_[64] = {0};
    uint8_t chipId_[16] = {0};
    size_t chipIdLen_ = 0;
    uint8_t coreCount_ = 0;
    uint32_t cpuFreqMHz_ = 0;
    bool initialized_ = false;

    void initialize();
    void readCpuInfo();
    void readMachineId();
    void readHostname();
    void readKernelVersion();
    uint8_t countCpuCores();
    uint32_t readCpuFrequency();
};

} // namespace hal
