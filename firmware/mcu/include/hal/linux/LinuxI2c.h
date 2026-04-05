// include/hal/linux/LinuxI2c.h
// Linux I2C implementation using /dev/i2c-* and ioctl
//
// Requires: i2c-tools, libi2c-dev (apt install i2c-tools libi2c-dev)
// Enable I2C via raspi-config or device tree on Raspberry Pi.
#pragma once

#include "../II2c.h"
#include <cstdint>
#include <cstring>

namespace hal {

/// Linux I2C implementation using /dev/i2c-* devices
///
/// Provides I2C communication via Linux's i2c-dev interface.
/// Uses ioctl for combined transactions (write-read).
///
/// Note: Requires user to be in i2c group, or run as root.
class LinuxI2c : public II2c {
public:
    /// Constructor
    /// @param busNumber I2C bus number (e.g., 1 for /dev/i2c-1)
    explicit LinuxI2c(int busNumber = 1);

    ~LinuxI2c();

    bool begin(uint8_t sda, uint8_t scl, uint32_t frequency = 100000) override;
    void end() override;
    void setFrequency(uint32_t frequency) override;
    bool devicePresent(uint8_t address) override;

    I2cResult write(uint8_t address, const uint8_t* data, size_t length, bool stop = true) override;
    I2cResult read(uint8_t address, uint8_t* data, size_t length) override;
    I2cResult writeRead(uint8_t address,
                        const uint8_t* writeData, size_t writeLen,
                        uint8_t* readData, size_t readLen) override;

    I2cResult writeReg(uint8_t address, uint8_t reg, uint8_t value) override;
    I2cResult readReg(uint8_t address, uint8_t reg, uint8_t* value) override;
    I2cResult readRegs(uint8_t address, uint8_t reg, uint8_t* data, size_t length) override;

private:
    int busNumber_;
    int fd_ = -1;
    uint32_t frequency_ = 100000;
    bool initialized_ = false;

    bool setSlaveAddress(uint8_t address);
    I2cResult mapError(int err);
};

} // namespace hal
