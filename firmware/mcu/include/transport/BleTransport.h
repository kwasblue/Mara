// core/BleTransport.h
#pragma once

#include <Arduino.h>
#include "core/ITransport.h"

#if HAS_BLE

#include <BluetoothSerial.h>
#include <vector>
#include "core/Protocol.h"
#include "core/Debug.h"

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error "Bluetooth is not enabled! Enable it in menuconfig or via build flags."
#endif

class BleTransport : public ITransport {
public:
    explicit BleTransport(const char* deviceName)
        : name_(deviceName) {}

    void begin() override {
        DBG_PRINTLN("[BleTransport] begin()");

        if (!SerialBT_.begin(name_)) {
            DBG_PRINTLN("[BleTransport] Failed to start BluetoothSerial");
            return;
        }

        DBG_PRINT("[BleTransport] Started as: ");
        DBG_PRINTLN(name_);

        rxBuffer_.clear();
        rxBuffer_.reserve(256);

        lastClientConnected_ = SerialBT_.hasClient();
        if (lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client already connected at begin()");
        }
    }

    void loop() override {
        bool hasClient = SerialBT_.hasClient();
        if (hasClient && !lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client connected");
        } else if (!hasClient && lastClientConnected_) {
            DBG_PRINTLN("[BleTransport] Client disconnected");
        }
        lastClientConnected_ = hasClient;

        while (SerialBT_.available()) {
            uint8_t b = static_cast<uint8_t>(SerialBT_.read());
            rxBuffer_.push_back(b);
            DBG_PRINTF("[BleTransport] RX byte: 0x%02X\n", b);
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
        if (!SerialBT_.hasClient()) {
            DBG_PRINTLN("[BleTransport] sendBytes: no client, skipping");
            return true;
        }
        DBG_PRINTF("[BleTransport] sendBytes len=%u\n", static_cast<unsigned>(len));
        size_t written = SerialBT_.write(data, len);
        SerialBT_.flush();
        DBG_PRINTF("[BleTransport] wrote=%u\n", static_cast<unsigned>(written));
        return (written == len);
    }

private:
    const char*          name_;
    BluetoothSerial      SerialBT_;
    std::vector<uint8_t> rxBuffer_;
    bool                 lastClientConnected_ = false;
};

#else // !HAS_BLE

// Stub when BLE is disabled - saves ~100KB flash
class BleTransport : public ITransport {
public:
    explicit BleTransport(const char*) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_BLE
