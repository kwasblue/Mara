// src/hal/linux/LinuxI2c.cpp
// Linux I2C implementation using /dev/i2c-* and ioctl

#include "hal/linux/LinuxI2c.h"

#if PLATFORM_LINUX

#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <cstdio>
#include <cerrno>

namespace hal {

LinuxI2c::LinuxI2c(int busNumber) : busNumber_(busNumber) {}

LinuxI2c::~LinuxI2c() {
    end();
}

bool LinuxI2c::begin(uint8_t sda, uint8_t scl, uint32_t frequency) {
    // On Linux, SDA/SCL pins are determined by the bus number, not configurable
    (void)sda;
    (void)scl;

    if (initialized_) {
        return true;
    }

    char device[32];
    snprintf(device, sizeof(device), "/dev/i2c-%d", busNumber_);

    fd_ = open(device, O_RDWR);
    if (fd_ < 0) {
        return false;
    }

    frequency_ = frequency;
    initialized_ = true;
    return true;
}

void LinuxI2c::end() {
    if (fd_ >= 0) {
        close(fd_);
        fd_ = -1;
    }
    initialized_ = false;
}

void LinuxI2c::setFrequency(uint32_t frequency) {
    frequency_ = frequency;
    // Note: Actual I2C frequency is typically set by the device tree/kernel
    // This is stored for informational purposes
}

bool LinuxI2c::devicePresent(uint8_t address) {
    if (!setSlaveAddress(address)) {
        return false;
    }

    // Try to read a byte - if device is present, this will succeed
    uint8_t dummy;
    return (read(fd_, &dummy, 1) == 1 || errno == ENXIO);
}

I2cResult LinuxI2c::write(uint8_t address, const uint8_t* data, size_t length, bool stop) {
    (void)stop;  // Linux always sends stop

    if (!initialized_) {
        return I2cResult::Unknown;
    }

    if (!setSlaveAddress(address)) {
        return I2cResult::NackAddr;
    }

    ssize_t written = ::write(fd_, data, length);
    if (written < 0) {
        return mapError(errno);
    }

    if (static_cast<size_t>(written) != length) {
        return I2cResult::NackData;
    }

    return I2cResult::Ok;
}

I2cResult LinuxI2c::read(uint8_t address, uint8_t* data, size_t length) {
    if (!initialized_) {
        return I2cResult::Unknown;
    }

    if (!setSlaveAddress(address)) {
        return I2cResult::NackAddr;
    }

    ssize_t bytesRead = ::read(fd_, data, length);
    if (bytesRead < 0) {
        return mapError(errno);
    }

    if (static_cast<size_t>(bytesRead) != length) {
        return I2cResult::Unknown;
    }

    return I2cResult::Ok;
}

I2cResult LinuxI2c::writeRead(uint8_t address,
                               const uint8_t* writeData, size_t writeLen,
                               uint8_t* readData, size_t readLen) {
    if (!initialized_) {
        return I2cResult::Unknown;
    }

    // Use I2C_RDWR ioctl for combined write-read
    struct i2c_msg msgs[2];
    struct i2c_rdwr_ioctl_data data;

    msgs[0].addr = address;
    msgs[0].flags = 0;  // Write
    msgs[0].len = writeLen;
    msgs[0].buf = const_cast<uint8_t*>(writeData);

    msgs[1].addr = address;
    msgs[1].flags = I2C_M_RD;  // Read
    msgs[1].len = readLen;
    msgs[1].buf = readData;

    data.msgs = msgs;
    data.nmsgs = 2;

    if (ioctl(fd_, I2C_RDWR, &data) < 0) {
        return mapError(errno);
    }

    return I2cResult::Ok;
}

I2cResult LinuxI2c::writeReg(uint8_t address, uint8_t reg, uint8_t value) {
    uint8_t buf[2] = {reg, value};
    return write(address, buf, 2);
}

I2cResult LinuxI2c::readReg(uint8_t address, uint8_t reg, uint8_t* value) {
    return writeRead(address, &reg, 1, value, 1);
}

I2cResult LinuxI2c::readRegs(uint8_t address, uint8_t reg, uint8_t* data, size_t length) {
    return writeRead(address, &reg, 1, data, length);
}

bool LinuxI2c::setSlaveAddress(uint8_t address) {
    if (ioctl(fd_, I2C_SLAVE, address) < 0) {
        // Try I2C_SLAVE_FORCE if I2C_SLAVE fails
        if (ioctl(fd_, I2C_SLAVE_FORCE, address) < 0) {
            return false;
        }
    }
    return true;
}

I2cResult LinuxI2c::mapError(int err) {
    switch (err) {
        case ENODEV:
        case ENXIO:
            return I2cResult::NackAddr;
        case ETIMEDOUT:
            return I2cResult::Timeout;
        case EIO:
            return I2cResult::BusError;
        case EOVERFLOW:
            return I2cResult::BufferOverflow;
        default:
            return I2cResult::Unknown;
    }
}

} // namespace hal

#endif // PLATFORM_LINUX
