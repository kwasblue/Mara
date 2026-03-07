#pragma once

#include "../II2c.h"

// Forward declare Arduino Wire class
class TwoWire;

namespace hal {

/// ESP32 I2C implementation using Wire library
class Esp32I2c : public II2c {
public:
    /// @param wireInstance Which Wire instance to use (0 = Wire, 1 = Wire1)
    explicit Esp32I2c(uint8_t wireInstance = 0);

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
    TwoWire* wire_ = nullptr;
    uint8_t wireInstance_;
    bool initialized_ = false;

    I2cResult translateError(uint8_t wireError);
};

} // namespace hal
