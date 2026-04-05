// src/hal/linux/LinuxPwm.cpp
// Linux PWM implementation using sysfs interface

#include "hal/linux/LinuxPwm.h"

#if PLATFORM_LINUX

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

namespace hal {

LinuxPwm::LinuxPwm(int pwmChip) : pwmChip_(pwmChip) {}

LinuxPwm::~LinuxPwm() {
    end();
}

bool LinuxPwm::begin() {
    // PWM chip should exist at /sys/class/pwm/pwmchipN
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/pwm/pwmchip%d", pwmChip_);
    return access(path, F_OK) == 0;
}

void LinuxPwm::end() {
    for (auto& [channel, state] : channels_) {
        if (state.exported) {
            unexportChannel(channel);
        }
    }
    channels_.clear();
}

bool LinuxPwm::attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution) {
    if (channel >= MAX_CHANNELS || frequency == 0) {
        return false;
    }

    // Export channel if not already
    if (!exportChannel(channel)) {
        return false;
    }

    ChannelState state;
    state.pin = pin;
    state.frequency = frequency;
    state.resolution = resolution;
    state.period_ns = 1000000000ULL / frequency;
    state.duty_ns = 0;
    state.exported = true;
    state.enabled = false;

    // Set period
    char path[256];
    buildChannelPath(path, sizeof(path), channel, "period");
    if (!writeToSysfs(path, state.period_ns)) {
        return false;
    }

    // Set initial duty cycle to 0
    buildChannelPath(path, sizeof(path), channel, "duty_cycle");
    if (!writeToSysfs(path, (uint64_t)0)) {
        return false;
    }

    // Enable the channel
    buildChannelPath(path, sizeof(path), channel, "enable");
    if (!writeToSysfs(path, "1")) {
        return false;
    }
    state.enabled = true;

    channels_[channel] = state;
    return true;
}

void LinuxPwm::detach(uint8_t channel) {
    auto it = channels_.find(channel);
    if (it == channels_.end()) {
        return;
    }

    // Disable before unexport
    char path[256];
    buildChannelPath(path, sizeof(path), channel, "enable");
    writeToSysfs(path, "0");

    unexportChannel(channel);
    channels_.erase(it);
}

void LinuxPwm::setDuty(uint8_t channel, float duty) {
    auto it = channels_.find(channel);
    if (it == channels_.end()) {
        return;
    }

    // Clamp duty to 0-100%
    if (duty < 0.0f) duty = 0.0f;
    if (duty > 100.0f) duty = 100.0f;

    uint64_t duty_ns = static_cast<uint64_t>(it->second.period_ns * duty / 100.0f);
    it->second.duty_ns = duty_ns;

    char path[256];
    buildChannelPath(path, sizeof(path), channel, "duty_cycle");
    writeToSysfs(path, duty_ns);
}

void LinuxPwm::setDutyRaw(uint8_t channel, uint32_t value) {
    auto it = channels_.find(channel);
    if (it == channels_.end()) {
        return;
    }

    uint32_t maxValue = (1U << it->second.resolution) - 1;
    float duty = (static_cast<float>(value) / maxValue) * 100.0f;
    setDuty(channel, duty);
}

void LinuxPwm::setFrequency(uint8_t channel, uint32_t frequency) {
    auto it = channels_.find(channel);
    if (it == channels_.end() || frequency == 0) {
        return;
    }

    // Calculate new period maintaining duty ratio
    float dutyRatio = (it->second.period_ns > 0)
        ? static_cast<float>(it->second.duty_ns) / it->second.period_ns
        : 0.0f;

    it->second.frequency = frequency;
    it->second.period_ns = 1000000000ULL / frequency;
    it->second.duty_ns = static_cast<uint64_t>(it->second.period_ns * dutyRatio);

    char path[256];
    buildChannelPath(path, sizeof(path), channel, "period");
    writeToSysfs(path, it->second.period_ns);

    buildChannelPath(path, sizeof(path), channel, "duty_cycle");
    writeToSysfs(path, it->second.duty_ns);
}

uint32_t LinuxPwm::getFrequency(uint8_t channel) {
    auto it = channels_.find(channel);
    return (it != channels_.end()) ? it->second.frequency : 0;
}

uint8_t LinuxPwm::getResolution(uint8_t channel) {
    auto it = channels_.find(channel);
    return (it != channels_.end()) ? it->second.resolution : 0;
}

uint8_t LinuxPwm::maxChannels() const {
    return MAX_CHANNELS;
}

bool LinuxPwm::exportChannel(uint8_t channel) {
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/pwm/pwmchip%d/export", pwmChip_);

    char value[16];
    snprintf(value, sizeof(value), "%u", channel);

    // Export may fail if already exported - that's OK
    writeToSysfs(path, value);

    // Check if channel directory exists
    snprintf(path, sizeof(path), "/sys/class/pwm/pwmchip%d/pwm%u", pwmChip_, channel);
    return access(path, F_OK) == 0;
}

bool LinuxPwm::unexportChannel(uint8_t channel) {
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/pwm/pwmchip%d/unexport", pwmChip_);

    char value[16];
    snprintf(value, sizeof(value), "%u", channel);
    return writeToSysfs(path, value);
}

bool LinuxPwm::writeToSysfs(const char* path, const char* value) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) {
        return false;
    }

    ssize_t len = strlen(value);
    ssize_t written = write(fd, value, len);
    close(fd);

    return written == len;
}

bool LinuxPwm::writeToSysfs(const char* path, uint64_t value) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%llu", (unsigned long long)value);
    return writeToSysfs(path, buf);
}

bool LinuxPwm::readFromSysfs(const char* path, uint64_t& value) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return false;
    }

    char buf[32];
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);

    if (n <= 0) {
        return false;
    }

    buf[n] = '\0';
    value = strtoull(buf, nullptr, 10);
    return true;
}

void LinuxPwm::buildChannelPath(char* buffer, size_t bufSize, uint8_t channel, const char* attr) {
    snprintf(buffer, bufSize, "/sys/class/pwm/pwmchip%d/pwm%u/%s", pwmChip_, channel, attr);
}

} // namespace hal

#endif // PLATFORM_LINUX
