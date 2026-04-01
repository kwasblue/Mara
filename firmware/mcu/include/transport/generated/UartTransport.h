// AUTO-GENERATED from TransportDef("uart")
// Implement init(), send(), and receive() with transport-specific logic
//
// To customize, copy this file to the parent directory and remove "_generated" suffix.

#pragma once

#include "config/FeatureFlags.h"

#if HAS_UART

#include "transport/ITransport.h"
#include <ArduinoJson.h>

namespace mara {

class UartTransport : public ITransport {
public:
    const char* name() const override { return "uart"; }
    const char* layer() const { return "physical"; }

    void init() override {
        // TODO: Initialize transport (physical layer)
        connected_ = false;
    }

    bool send(const uint8_t* data, size_t len) override {
        // TODO: Send data over transport
        return false;
    }

    size_t receive(uint8_t* buffer, size_t maxLen) override {
        // TODO: Receive data from transport
        return 0;
    }

    bool isConnected() const override { return connected_; }

private:
    bool connected_ = false;
};

} // namespace mara

#endif // HAS_UART
