// include/transport/MultiTransport.h
// Multi-transport aggregator with response routing
//
// =============================================================================
// TRANSPORT CONTRACT
// =============================================================================
//
// FRAME ROUTING:
//   - Incoming frames from ANY transport are delivered to the single frame handler
//   - The transport that received the frame is tracked for response routing
//   - Responses are sent ONLY to the originating transport (not broadcast)
//
// RESPONSE SEMANTICS:
//   - sendBytes() sends to the LAST transport that delivered a frame
//   - sendBytesToAll() broadcasts to ALL connected transports
//   - If no frame has been received yet, sendBytes() broadcasts
//
// DUPLICATE COMMAND PREVENTION:
//   - CommandContext handles duplicate detection via ACK cache
//   - Same command from different transports gets same cached ACK
//   - No special handling needed here - ACK cache is transport-agnostic
//
// FRAME SIZE LIMITS:
//   - Max frame size: 1024 bytes (Protocol::MAX_FRAME_SIZE)
//   - Larger frames will be rejected by Protocol::extractFrames()
//
// QUEUE BEHAVIOR:
//   - No internal queuing in MultiTransport
//   - Each underlying transport handles its own buffering
//   - Backpressure handled by transport-specific mechanisms:
//     - UART: Hardware flow control (if enabled) or drop
//     - WiFi: TCP backpressure / connection drop
//     - BLE: Notify queue limits
//
// =============================================================================

#pragma once

#include <vector>
#include <cstdint>
#include "core/ITransport.h"

class MultiTransport : public ITransport {
public:
    /// Add a transport to the aggregator
    void addTransport(ITransport* t) {
        if (t) {
            transports_.push_back(t);
        }
    }

    /// Initialize all transports
    void begin() override {
        for (size_t i = 0; i < transports_.size(); ++i) {
            ITransport* t = transports_[i];
            if (!t) continue;

            // Wire frame handler to track originating transport
            t->setFrameHandler([this, i](const uint8_t* data, size_t len) {
                lastReceiveTransportIdx_ = i;
                if (this->handler_) {
                    this->handler_(data, len);
                }
            });
            t->begin();
        }
    }

    /// Poll all transports
    void loop() override {
        for (auto* t : transports_) {
            if (t) t->loop();
        }
    }

    /// Send bytes to the originating transport (or broadcast if unknown)
    bool sendBytes(const uint8_t* data, size_t len) override {
        if (lastReceiveTransportIdx_ < transports_.size()) {
            // Send only to the transport that last received a frame
            ITransport* t = transports_[lastReceiveTransportIdx_];
            if (t) {
                return t->sendBytes(data, len);
            }
        }
        // Fallback: broadcast to all
        return sendBytesToAll(data, len);
    }

    /// Broadcast to all transports
    bool sendBytesToAll(const uint8_t* data, size_t len) {
        bool ok = true;
        for (auto* t : transports_) {
            if (t) {
                ok = t->sendBytes(data, len) && ok;
            }
        }
        return ok;
    }

    /// Get number of registered transports
    size_t transportCount() const { return transports_.size(); }

    /// Get transport by index (for diagnostics)
    ITransport* getTransport(size_t idx) {
        if (idx < transports_.size()) return transports_[idx];
        return nullptr;
    }

    /// Get index of last transport that received a frame
    size_t lastReceiveTransportIndex() const { return lastReceiveTransportIdx_; }

private:
    std::vector<ITransport*> transports_;
    size_t lastReceiveTransportIdx_ = SIZE_MAX;  // Invalid until first receive
};
