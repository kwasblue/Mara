#pragma once

#include <cstdint>
#include <cstddef>
#include <functional>

namespace hal {

/// CAN message structure
struct CanMessage {
    uint32_t id;            // 11-bit standard or 29-bit extended ID
    uint8_t  data[8];       // Payload (up to 8 bytes for CAN 2.0)
    uint8_t  len;           // Data length (0-8)
    bool     extended;      // True if 29-bit extended ID
    bool     rtr;           // Remote transmission request
};

/// CAN bus state
enum class CanState : uint8_t {
    STOPPED = 0,
    RUNNING,
    BUS_OFF,        // Bus-off due to errors
    RECOVERING      // Recovering from bus-off
};

/// CAN error counters
struct CanErrors {
    uint32_t txErrors;
    uint32_t rxErrors;
    uint32_t busOffCount;
    uint32_t arbitrationLost;
};

/// Callback for received messages
using CanReceiveCallback = std::function<void(const CanMessage&)>;

/**
 * ICan - Abstract CAN bus interface
 *
 * Platform-agnostic interface for CAN 2.0B communication.
 * Implementations:
 *   - Esp32Can: Uses ESP-IDF TWAI driver
 *   - [Future] Stm32Can: Uses STM32 bxCAN peripheral
 *
 * Example usage:
 *   hal::ICan* can = &hal.can;
 *   can->begin(500000);  // 500 kbps
 *
 *   CanMessage msg = {.id = 0x100, .len = 4};
 *   msg.data[0] = 0x01;
 *   can->send(msg);
 */
class ICan {
public:
    virtual ~ICan() = default;

    // ===== Lifecycle =====

    /**
     * Initialize CAN bus at specified baud rate.
     * Common rates: 125000, 250000, 500000, 1000000
     * @param baudRate Bits per second
     * @return true on success
     */
    virtual bool begin(uint32_t baudRate = 500000) = 0;

    /**
     * Stop CAN bus and release resources.
     */
    virtual void end() = 0;

    /**
     * Get current bus state.
     */
    virtual CanState getState() const = 0;

    /**
     * Attempt to recover from bus-off state.
     * @return true if recovery initiated
     */
    virtual bool recover() = 0;

    // ===== Transmit =====

    /**
     * Send a CAN message.
     * @param msg Message to send
     * @param timeoutMs Timeout in milliseconds (0 = non-blocking)
     * @return true if queued/sent successfully
     */
    virtual bool send(const CanMessage& msg, uint32_t timeoutMs = 10) = 0;

    /**
     * Send with simple parameters (convenience method).
     */
    bool send(uint32_t id, const uint8_t* data, uint8_t len, uint32_t timeoutMs = 10) {
        CanMessage msg = {};
        msg.id = id;
        msg.len = len > 8 ? 8 : len;
        for (uint8_t i = 0; i < msg.len; i++) {
            msg.data[i] = data[i];
        }
        return send(msg, timeoutMs);
    }

    /**
     * Check if transmit queue has space.
     */
    virtual bool canSend() const = 0;

    // ===== Receive =====

    /**
     * Check if messages are available in receive queue.
     */
    virtual int available() const = 0;

    /**
     * Receive a message from the queue.
     * @param msg Output message
     * @param timeoutMs Timeout in milliseconds (0 = non-blocking)
     * @return true if message received
     */
    virtual bool receive(CanMessage& msg, uint32_t timeoutMs = 0) = 0;

    /**
     * Set callback for received messages (interrupt context).
     * Note: Callback runs in ISR context - keep it fast!
     */
    virtual void setReceiveCallback(CanReceiveCallback callback) = 0;

    // ===== Filtering =====

    /**
     * Set acceptance filter.
     * Only messages matching (id & mask) == (filter & mask) are received.
     * @param filter Filter value
     * @param mask Mask value (1 = must match, 0 = don't care)
     * @param extended True for 29-bit IDs
     */
    virtual void setFilter(uint32_t filter, uint32_t mask, bool extended = false) = 0;

    /**
     * Accept all messages (clear filters).
     */
    virtual void clearFilters() = 0;

    // ===== Status =====

    /**
     * Get error counters.
     */
    virtual CanErrors getErrors() const = 0;

    /**
     * Reset error counters.
     */
    virtual void resetErrors() = 0;

    /**
     * Check if bus is in error state.
     */
    virtual bool hasError() const = 0;
};

} // namespace hal
