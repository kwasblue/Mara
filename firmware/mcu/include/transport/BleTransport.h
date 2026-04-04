// include/transport/BleTransport.h
// Bluetooth Serial (SPP) transport using HAL interfaces
#pragma once

#include "config/FeatureFlags.h"
#include "core/ITransport.h"

#if HAS_BLE

#include <vector>
#include "core/Protocol.h"
#include "core/Debug.h"
#include "hal/IBleByteStream.h"

/// Bluetooth Serial (SPP) transport using HAL interfaces.
/// Platform-agnostic: works with any IBleByteStream implementation.
class BleTransport : public ITransport {
public:
    /// @param stream BLE byte stream (caller retains ownership)
    explicit BleTransport(hal::IBleByteStream* stream)
        : stream_(stream) {}

    void begin() override {
        if (!stream_ || initialized_) {
            if (initialized_) {
                DBG_PRINTLN("[BleTransport] begin() - already initialized, skipping");
            }
            return;
        }

        DBG_PRINTLN("[BleTransport] begin()");

        stream_->begin();
        initialized_ = true;

        rxBuffer_.clear();
        rxBuffer_.reserve(256);

        lastClientConnected_ = stream_->hasClient();
        if (lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client already connected at begin()");
        }
    }

    void loop() override {
        if (!stream_) return;

        bool hasClient = stream_->hasClient();
        if (hasClient && !lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client connected");
        } else if (!hasClient && lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client disconnected");
        }
        lastClientConnected_ = hasClient;

        while (stream_->available() > 0) {
            int b = stream_->read();
            if (b >= 0) {
                rxBuffer_.push_back(static_cast<uint8_t>(b));
                DBG_PRINTF("[BleTransport] RX byte: 0x%02X\n", static_cast<uint8_t>(b));
            }
        }

        if (handler_ && !rxBuffer_.empty()) {
            Protocol::extractFrames(
                rxBuffer_,
                [this](const uint8_t* frame, size_t len) {
                    DBG_PRINTF("[BleTransport] Extracted frame, len=%u\n",
                               static_cast<unsigned>(len));
                    handler_(frame, len);
                }
            );
        }
    }

    bool sendBytes(const uint8_t* data, size_t len) override {
        if (!stream_ || !stream_->hasClient()) {
            DBG_PRINTLN("[BleTransport] sendBytes: no client, skipping");
            return true;
        }
        DBG_PRINTF("[BleTransport] sendBytes len=%u\n", static_cast<unsigned>(len));
        size_t written = stream_->write(data, len);
        stream_->flush();
        DBG_PRINTF("[BleTransport] wrote=%u\n", static_cast<unsigned>(written));
        return (written == len);
    }

private:
    hal::IBleByteStream* stream_ = nullptr;
    std::vector<uint8_t> rxBuffer_;
    bool                 lastClientConnected_ = false;
    bool                 initialized_ = false;
};

#else // !HAS_BLE

#include "hal/IBleByteStream.h"

// Stub when BLE is disabled - saves ~100KB flash
class BleTransport : public ITransport {
public:
    explicit BleTransport(hal::IBleByteStream*) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_BLE
