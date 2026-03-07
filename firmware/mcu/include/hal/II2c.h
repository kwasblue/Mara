#pragma once

#include <cstdint>
#include <cstddef>

namespace hal {

/// I2C operation result
enum class I2cResult : uint8_t {
    Ok = 0,
    NackAddr,       // Device not responding (address NACK)
    NackData,       // Data NACK
    Timeout,
    BusError,
    BufferOverflow,
    Unknown
};

/// Abstract I2C bus interface for platform portability
class II2c {
public:
    virtual ~II2c() = default;

    /// Initialize I2C bus
    /// @param sda SDA pin
    /// @param scl SCL pin
    /// @param frequency Clock frequency in Hz (default 100kHz)
    /// @return true if successful
    virtual bool begin(uint8_t sda, uint8_t scl, uint32_t frequency = 100000) = 0;

    /// Deinitialize I2C bus
    virtual void end() = 0;

    /// Set clock frequency
    virtual void setFrequency(uint32_t frequency) = 0;

    /// Check if device is present at address
    /// @param address 7-bit I2C address
    /// @return true if device ACKs
    virtual bool devicePresent(uint8_t address) = 0;

    /// Write data to device
    /// @param address 7-bit I2C address
    /// @param data Data buffer to write
    /// @param length Number of bytes to write
    /// @param stop Send stop condition (default true)
    /// @return I2cResult
    virtual I2cResult write(uint8_t address, const uint8_t* data, size_t length, bool stop = true) = 0;

    /// Read data from device
    /// @param address 7-bit I2C address
    /// @param data Buffer to store read data
    /// @param length Number of bytes to read
    /// @return I2cResult
    virtual I2cResult read(uint8_t address, uint8_t* data, size_t length) = 0;

    /// Write then read (combined transaction)
    /// @param address 7-bit I2C address
    /// @param writeData Data to write
    /// @param writeLen Number of bytes to write
    /// @param readData Buffer for read data
    /// @param readLen Number of bytes to read
    /// @return I2cResult
    virtual I2cResult writeRead(uint8_t address,
                                 const uint8_t* writeData, size_t writeLen,
                                 uint8_t* readData, size_t readLen) = 0;

    /// Write single byte to register
    virtual I2cResult writeReg(uint8_t address, uint8_t reg, uint8_t value) = 0;

    /// Read single byte from register
    virtual I2cResult readReg(uint8_t address, uint8_t reg, uint8_t* value) = 0;

    /// Read multiple bytes from register
    virtual I2cResult readRegs(uint8_t address, uint8_t reg, uint8_t* data, size_t length) = 0;
};

} // namespace hal
