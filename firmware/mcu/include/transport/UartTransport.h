#pragma once

#include "config/FeatureFlags.h"

#if HAS_UART_TRANSPORT

#include <vector>
#include "core/ITransport.h"
#include "core/Protocol.h"
#include "hal/IByteStream.h"

/// UART transport using HAL byte stream interface.
/// Platform-agnostic: works with any IByteStream implementation.
class UartTransport : public ITransport {
public:
    /// @param stream Byte stream (caller retains ownership)
    /// @param baud Baud rate to initialize stream with
    UartTransport(hal::IByteStream* stream, uint32_t baud)
        : stream_(stream), baud_(baud) {}

    void begin() override {
        if (stream_) {
            stream_->begin(baud_);
        }
        rxBuffer_.clear();
        rxBuffer_.reserve(256);
    }

    void loop() override {
        if (!stream_) return;

        while (stream_->available() > 0) {
            int b = stream_->read();
            if (b >= 0) {
                rxBuffer_.push_back(static_cast<uint8_t>(b));
            }
        }

        if (!handler_) return;

        Protocol::extractFrames(rxBuffer_, [this](const uint8_t* frame, size_t len) {
            handler_(frame, len);
        });
    }

    bool sendBytes(const uint8_t* data, size_t len) override {
        if (!stream_) return false;
        size_t written = stream_->write(data, len);
        return written == len;
    }

private:
    hal::IByteStream*     stream_;
    uint32_t              baud_;
    std::vector<uint8_t>  rxBuffer_;
};

#else // !HAS_UART_TRANSPORT

#include "core/ITransport.h"
#include "hal/IByteStream.h"

// Stub when UART is disabled
class UartTransport : public ITransport {
public:
    UartTransport(hal::IByteStream*, uint32_t) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_UART_TRANSPORT
