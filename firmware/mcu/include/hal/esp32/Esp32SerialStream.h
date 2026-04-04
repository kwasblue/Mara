// include/hal/esp32/Esp32SerialStream.h
// ESP32 serial stream implementation wrapping HardwareSerial
#pragma once

#include "../IByteStream.h"
#include <Arduino.h>

namespace hal {

/// ESP32 serial stream implementation wrapping Arduino HardwareSerial
class Esp32SerialStream : public IByteStream {
public:
    explicit Esp32SerialStream(HardwareSerial& serial)
        : serial_(serial) {}

    void begin(uint32_t baud = 0) override {
        if (baud > 0) {
            serial_.begin(baud);
        }
    }

    int available() override {
        return serial_.available();
    }

    int read() override {
        return serial_.read();
    }

    size_t write(const uint8_t* data, size_t len) override {
        return serial_.write(data, len);
    }

    void flush() override {
        serial_.flush();
    }

    void end() override {
        serial_.end();
    }

private:
    HardwareSerial& serial_;
};

} // namespace hal
