// include/hal/linux/LinuxPwm.h
// Linux PWM implementation using sysfs interface
//
// PWM is exposed via /sys/class/pwm/pwmchipN/
// Requires: PWM overlay enabled in device tree
#pragma once

#include "../IPwm.h"
#include <cstdint>
#include <map>

namespace hal {

/// Linux PWM implementation using sysfs
///
/// Provides PWM control via /sys/class/pwm/pwmchipN/pwmM/
/// Each PWM chip can have multiple channels.
///
/// On Raspberry Pi, enable PWM via:
///   dtoverlay=pwm-2chan in /boot/config.txt
///
/// Note: Requires write access to /sys/class/pwm (root or pwm group)
class LinuxPwm : public IPwm {
public:
    /// Constructor
    /// @param pwmChip PWM chip number (default: 0)
    explicit LinuxPwm(int pwmChip = 0);

    ~LinuxPwm();

    bool attach(uint8_t channel, uint8_t pin, uint32_t frequency, uint8_t resolution = 12) override;
    void detach(uint8_t channel) override;
    void setDuty(uint8_t channel, float duty) override;
    void setDutyRaw(uint8_t channel, uint32_t value) override;
    void setFrequency(uint8_t channel, uint32_t frequency) override;
    uint32_t getFrequency(uint8_t channel) override;
    uint8_t getResolution(uint8_t channel) override;
    uint8_t maxChannels() const override;

    /// Initialize the PWM subsystem
    bool begin();

    /// Clean up PWM resources
    void end();

private:
    struct ChannelState {
        uint8_t pin = 0;
        uint32_t frequency = 0;
        uint8_t resolution = 12;
        uint32_t period_ns = 0;
        uint32_t duty_ns = 0;
        bool exported = false;
        bool enabled = false;
    };

    int pwmChip_;
    std::map<uint8_t, ChannelState> channels_;
    static constexpr uint8_t MAX_CHANNELS = 16;

    bool exportChannel(uint8_t channel);
    bool unexportChannel(uint8_t channel);
    bool writeToSysfs(const char* path, const char* value);
    bool writeToSysfs(const char* path, uint64_t value);
    bool readFromSysfs(const char* path, uint64_t& value);
    void buildChannelPath(char* buffer, size_t bufSize, uint8_t channel, const char* attr);
};

} // namespace hal
