// test/fakes/FakeTransport.h
#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
#include "core/ITransport.h"

class FakeTransport final : public ITransport {
public:
    std::vector<uint8_t> tx;   // last transmitted payload
    int sendCount = 0;

    void begin() override {}
    void loop() override {}

    bool sendBytes(const uint8_t* data, size_t len) override {
        tx.assign(data, data + len);
        sendCount++;
        return true;
    }

    // Simulate receiving a frame from the wire
    void injectRx(const uint8_t* data, size_t len) {
        if (handler_) handler_(data, len);
    }
};
