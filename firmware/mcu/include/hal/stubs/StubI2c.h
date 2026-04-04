// include/hal/stubs/StubI2c.h
// Stub I2C implementation for native/test builds
#pragma once

#include "../II2c.h"

namespace hal {

class StubI2c : public II2c {
public:
    bool begin(uint8_t sda, uint8_t scl, uint32_t frequency = 100000) override {
        (void)sda; (void)scl; (void)frequency;
        return true;
    }

    void end() override {}
    void setFrequency(uint32_t frequency) override { (void)frequency; }
    bool devicePresent(uint8_t address) override { (void)address; return false; }

    I2cResult write(uint8_t address, const uint8_t* data, size_t length, bool stop = true) override {
        (void)address; (void)data; (void)length; (void)stop;
        return I2cResult::Ok;
    }

    I2cResult read(uint8_t address, uint8_t* data, size_t length) override {
        (void)address; (void)data; (void)length;
        return I2cResult::Ok;
    }

    I2cResult writeRead(uint8_t address,
                        const uint8_t* writeData, size_t writeLen,
                        uint8_t* readData, size_t readLen) override {
        (void)address; (void)writeData; (void)writeLen; (void)readData; (void)readLen;
        return I2cResult::Ok;
    }

    I2cResult writeReg(uint8_t address, uint8_t reg, uint8_t value) override {
        (void)address; (void)reg; (void)value;
        return I2cResult::Ok;
    }

    I2cResult readReg(uint8_t address, uint8_t reg, uint8_t* value) override {
        (void)address; (void)reg; (void)value;
        return I2cResult::Ok;
    }

    I2cResult readRegs(uint8_t address, uint8_t reg, uint8_t* data, size_t length) override {
        (void)address; (void)reg; (void)data; (void)length;
        return I2cResult::Ok;
    }
};

} // namespace hal
