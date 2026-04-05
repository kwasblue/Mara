// src/hal/linux/LinuxSystemInfo.cpp
// Linux system info implementation

#include "hal/linux/LinuxSystemInfo.h"

#if PLATFORM_LINUX

#include <cstdio>
#include <cstring>
#include <fstream>
#include <unistd.h>
#include <sys/utsname.h>

namespace hal {

LinuxSystemInfo::LinuxSystemInfo() {
    initialize();
}

void LinuxSystemInfo::initialize() {
    if (initialized_) return;

    readCpuInfo();
    readMachineId();
    readHostname();
    readKernelVersion();
    coreCount_ = countCpuCores();
    cpuFreqMHz_ = readCpuFrequency();

    initialized_ = true;
}

ResetReason LinuxSystemInfo::getResetReason() {
    // Linux doesn't have reset reasons like MCU
    return ResetReason::PowerOn;
}

ResetReason LinuxSystemInfo::getResetReason(uint8_t core) {
    (void)core;
    return ResetReason::PowerOn;
}

uint8_t LinuxSystemInfo::getResetReasonRaw(uint8_t core) {
    (void)core;
    return 0;
}

const char* LinuxSystemInfo::getChipModel() {
    return chipModel_;
}

uint8_t LinuxSystemInfo::getChipRevision() {
    return 0;  // Not applicable on Linux
}

uint8_t LinuxSystemInfo::getCoreCount() {
    return coreCount_;
}

uint32_t LinuxSystemInfo::getCpuFreqMHz() {
    return cpuFreqMHz_;
}

size_t LinuxSystemInfo::getChipId(uint8_t* id, size_t maxLen) {
    size_t copyLen = (chipIdLen_ < maxLen) ? chipIdLen_ : maxLen;
    memcpy(id, chipId_, copyLen);
    return copyLen;
}

uint64_t LinuxSystemInfo::getTotalRam() {
    std::ifstream meminfo("/proc/meminfo");
    if (!meminfo.is_open()) {
        return 0;
    }

    std::string line;
    while (std::getline(meminfo, line)) {
        if (line.find("MemTotal:") == 0) {
            uint64_t kb = 0;
            sscanf(line.c_str(), "MemTotal: %lu", &kb);
            return kb * 1024;
        }
    }
    return 0;
}

uint64_t LinuxSystemInfo::getAvailableRam() {
    std::ifstream meminfo("/proc/meminfo");
    if (!meminfo.is_open()) {
        return 0;
    }

    std::string line;
    while (std::getline(meminfo, line)) {
        if (line.find("MemAvailable:") == 0) {
            uint64_t kb = 0;
            sscanf(line.c_str(), "MemAvailable: %lu", &kb);
            return kb * 1024;
        }
    }
    return 0;
}

uint64_t LinuxSystemInfo::getUptime() {
    std::ifstream uptime("/proc/uptime");
    if (!uptime.is_open()) {
        return 0;
    }

    double seconds = 0;
    uptime >> seconds;
    return static_cast<uint64_t>(seconds);
}

const char* LinuxSystemInfo::getHostname() {
    return hostname_;
}

const char* LinuxSystemInfo::getKernelVersion() {
    return kernelVersion_;
}

void LinuxSystemInfo::readCpuInfo() {
    std::ifstream cpuinfo("/proc/cpuinfo");
    if (!cpuinfo.is_open()) {
        strcpy(chipModel_, "Unknown");
        return;
    }

    std::string line;
    while (std::getline(cpuinfo, line)) {
        // Try different fields that might contain model info
        if (line.find("Model") == 0 || line.find("model name") == 0) {
            size_t colon = line.find(':');
            if (colon != std::string::npos) {
                const char* value = line.c_str() + colon + 1;
                while (*value == ' ' || *value == '\t') value++;
                strncpy(chipModel_, value, sizeof(chipModel_) - 1);
                chipModel_[sizeof(chipModel_) - 1] = '\0';
                return;
            }
        }
    }

    // Fallback: try to get from uname
    struct utsname uts;
    if (uname(&uts) == 0) {
        snprintf(chipModel_, sizeof(chipModel_), "%.32s %.31s", uts.sysname, uts.machine);
    } else {
        strcpy(chipModel_, "Linux");
    }
}

void LinuxSystemInfo::readMachineId() {
    // Try /etc/machine-id first (most distros)
    std::ifstream machineId("/etc/machine-id");
    if (machineId.is_open()) {
        std::string id;
        std::getline(machineId, id);

        // machine-id is 32 hex characters, convert to 16 bytes
        chipIdLen_ = 0;
        for (size_t i = 0; i + 1 < id.size() && chipIdLen_ < sizeof(chipId_); i += 2) {
            unsigned int byte;
            if (sscanf(id.c_str() + i, "%02x", &byte) == 1) {
                chipId_[chipIdLen_++] = static_cast<uint8_t>(byte);
            }
        }
        return;
    }

    // Fallback: try Raspberry Pi serial from /proc/cpuinfo
    std::ifstream cpuinfo("/proc/cpuinfo");
    if (cpuinfo.is_open()) {
        std::string line;
        while (std::getline(cpuinfo, line)) {
            if (line.find("Serial") == 0) {
                size_t colon = line.find(':');
                if (colon != std::string::npos) {
                    const char* serial = line.c_str() + colon + 1;
                    while (*serial == ' ' || *serial == '\t') serial++;

                    chipIdLen_ = 0;
                    while (*serial && chipIdLen_ < sizeof(chipId_)) {
                        unsigned int byte;
                        if (sscanf(serial, "%02x", &byte) == 1) {
                            chipId_[chipIdLen_++] = static_cast<uint8_t>(byte);
                            serial += 2;
                        } else {
                            break;
                        }
                    }
                    return;
                }
            }
        }
    }

    // Last resort: use zeros
    memset(chipId_, 0, sizeof(chipId_));
    chipIdLen_ = 16;
}

void LinuxSystemInfo::readHostname() {
    if (gethostname(hostname_, sizeof(hostname_)) != 0) {
        strcpy(hostname_, "localhost");
    }
    hostname_[sizeof(hostname_) - 1] = '\0';
}

void LinuxSystemInfo::readKernelVersion() {
    struct utsname uts;
    if (uname(&uts) == 0) {
        snprintf(kernelVersion_, sizeof(kernelVersion_), "%.*s",
                 static_cast<int>(sizeof(kernelVersion_) - 1), uts.release);
    } else {
        strcpy(kernelVersion_, "unknown");
    }
}

uint8_t LinuxSystemInfo::countCpuCores() {
    // Use sysconf for reliable count
    long cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (cores > 0 && cores <= 255) {
        return static_cast<uint8_t>(cores);
    }
    return 1;
}

uint32_t LinuxSystemInfo::readCpuFrequency() {
    // Try scaling_max_freq first (in kHz)
    std::ifstream freq("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq");
    if (freq.is_open()) {
        uint32_t khz = 0;
        freq >> khz;
        return khz / 1000;  // Convert to MHz
    }

    // Fallback: parse /proc/cpuinfo
    std::ifstream cpuinfo("/proc/cpuinfo");
    if (cpuinfo.is_open()) {
        std::string line;
        while (std::getline(cpuinfo, line)) {
            if (line.find("cpu MHz") == 0) {
                size_t colon = line.find(':');
                if (colon != std::string::npos) {
                    float mhz = 0;
                    sscanf(line.c_str() + colon + 1, "%f", &mhz);
                    return static_cast<uint32_t>(mhz);
                }
            }
        }
    }

    return 0;  // Unknown
}

} // namespace hal

#endif // PLATFORM_LINUX
