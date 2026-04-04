// include/hal/esp32/Esp32BluetoothStream.h
// ESP32 Bluetooth Serial stream implementation
#pragma once

#include "config/FeatureFlags.h"

#if HAS_BLE

#include "../IBleByteStream.h"
#include <BluetoothSerial.h>
#include <esp32-hal-bt.h>

namespace hal {

/// ESP32 Bluetooth Serial stream implementation wrapping BluetoothSerial (SPP)
class Esp32BluetoothStream : public IBleByteStream {
public:
    explicit Esp32BluetoothStream(const char* deviceName)
        : deviceName_(deviceName) {}

    void begin(uint32_t baud = 0) override {
        (void)baud; // BT doesn't use baud rate

        if (initialized_) {
            return;
        }

        // Start BT controller if not already running
        if (!btStarted()) {
            if (!btStart()) {
                return;
            }
        }

        // Start in slave mode
        if (serialBT_.begin(deviceName_, false)) {
            initialized_ = true;
        }
    }

    int available() override {
        return serialBT_.available();
    }

    int read() override {
        return serialBT_.read();
    }

    size_t write(const uint8_t* data, size_t len) override {
        size_t written = serialBT_.write(data, len);
        serialBT_.flush();
        return written;
    }

    void flush() override {
        serialBT_.flush();
    }

    void end() override {
        serialBT_.end();
        initialized_ = false;
    }

    /// Check if a BT client is connected
    bool hasClient() const override {
        return serialBT_.hasClient();
    }

    /// Set authentication complete callback
    void onAuthComplete(void (*callback)(bool success)) {
        serialBT_.onAuthComplete(callback);
    }

    /// Get underlying BluetoothSerial for advanced configuration
    BluetoothSerial& underlying() { return serialBT_; }

private:
    const char* deviceName_;
    mutable BluetoothSerial serialBT_;  // mutable for hasClient() const
    bool initialized_ = false;
};

} // namespace hal

#else // !HAS_BLE

#include "../IBleByteStream.h"

namespace hal {

// Stub when BLE is disabled
class Esp32BluetoothStream : public IBleByteStream {
public:
    explicit Esp32BluetoothStream(const char*) {}
    void begin(uint32_t = 0) override {}
    int available() override { return 0; }
    int read() override { return -1; }
    size_t write(const uint8_t*, size_t) override { return 0; }
    bool hasClient() const override { return false; }
    void onAuthComplete(void (*)(bool)) {}
};

} // namespace hal

#endif // HAS_BLE
