#pragma once

#include "config/FeatureFlags.h"

#if HAS_UART_TRANSPORT

#include <Arduino.h>
#include <vector>
#include "core/ITransport.h"
#include "core/Protocol.h"

class UartTransport : public ITransport {
public:
    UartTransport(HardwareSerial& serial, uint32_t baud)
        : serial_(serial), baud_(baud) {}

    void begin() override {
        serial_.begin(baud_);
        rxBuffer_.clear();
        rxBuffer_.reserve(256);
    }

    void loop() override {
        while (serial_.available() > 0) {
            uint8_t b = static_cast<uint8_t>(serial_.read());
            rxBuffer_.push_back(b);
        }

        if (!handler_) return;

        Protocol::extractFrames(rxBuffer_, [this](const uint8_t* frame, size_t len) {
            handler_(frame, len);
        });
    }

    bool sendBytes(const uint8_t* data, size_t len) override {
        size_t written = serial_.write(data, len);
        return written == len;
    }

private:
    HardwareSerial&       serial_;
    uint32_t              baud_;
    std::vector<uint8_t>  rxBuffer_;
};

#else // !HAS_UART_TRANSPORT

#include "core/ITransport.h"

// Stub when UART is disabled
class UartTransport : public ITransport {
public:
    UartTransport(HardwareSerial&, uint32_t) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_UART_TRANSPORT
