#include "hal/esp32/Esp32I2c.h"
#include <Wire.h>

namespace hal {

Esp32I2c::Esp32I2c(uint8_t wireInstance) : wireInstance_(wireInstance) {
    if (wireInstance == 0) {
        wire_ = &Wire;
    } else {
        wire_ = &Wire1;
    }
}

bool Esp32I2c::begin(uint8_t sda, uint8_t scl, uint32_t frequency) {
    if (initialized_) {
        return true;  // Already initialized
    }

    bool ok = wire_->begin(sda, scl, frequency);
    if (ok) {
        initialized_ = true;
    }
    return ok;
}

void Esp32I2c::end() {
    if (initialized_) {
        wire_->end();
        initialized_ = false;
    }
}

void Esp32I2c::setFrequency(uint32_t frequency) {
    wire_->setClock(frequency);
}

bool Esp32I2c::devicePresent(uint8_t address) {
    wire_->beginTransmission(address);
    return wire_->endTransmission() == 0;
}

I2cResult Esp32I2c::translateError(uint8_t wireError) {
    switch (wireError) {
        case 0: return I2cResult::Ok;
        case 1: return I2cResult::BufferOverflow;  // Data too long
        case 2: return I2cResult::NackAddr;        // NACK on address
        case 3: return I2cResult::NackData;        // NACK on data
        case 4: return I2cResult::BusError;        // Other error
        case 5: return I2cResult::Timeout;         // Timeout
        default: return I2cResult::Unknown;
    }
}

I2cResult Esp32I2c::write(uint8_t address, const uint8_t* data, size_t length, bool stop) {
    wire_->beginTransmission(address);
    wire_->write(data, length);
    uint8_t err = wire_->endTransmission(stop);
    return translateError(err);
}

I2cResult Esp32I2c::read(uint8_t address, uint8_t* data, size_t length) {
    size_t received = wire_->requestFrom(address, length);
    if (received != length) {
        return I2cResult::NackAddr;
    }
    for (size_t i = 0; i < length; i++) {
        data[i] = wire_->read();
    }
    return I2cResult::Ok;
}

I2cResult Esp32I2c::writeRead(uint8_t address,
                               const uint8_t* writeData, size_t writeLen,
                               uint8_t* readData, size_t readLen) {
    // Write without stop
    I2cResult result = write(address, writeData, writeLen, false);
    if (result != I2cResult::Ok) {
        return result;
    }

    // Read with stop
    return read(address, readData, readLen);
}

I2cResult Esp32I2c::writeReg(uint8_t address, uint8_t reg, uint8_t value) {
    uint8_t data[2] = {reg, value};
    return write(address, data, 2);
}

I2cResult Esp32I2c::readReg(uint8_t address, uint8_t reg, uint8_t* value) {
    return writeRead(address, &reg, 1, value, 1);
}

I2cResult Esp32I2c::readRegs(uint8_t address, uint8_t reg, uint8_t* data, size_t length) {
    return writeRead(address, &reg, 1, data, length);
}

} // namespace hal
