#pragma once

#include "config/FeatureFlags.h"

#if HAS_CAN

#include "../ICan.h"
#include <driver/twai.h>

// Default CAN pins (can be overridden in PinConfig.h or platformio.ini)
#ifndef CAN_TX_PIN
#define CAN_TX_PIN 5
#endif

#ifndef CAN_RX_PIN
#define CAN_RX_PIN 4
#endif

namespace hal {

/**
 * Esp32Can - ESP32 TWAI (CAN) driver implementation
 *
 * Uses the ESP-IDF TWAI driver for CAN 2.0B communication.
 * TWAI = Two-Wire Automotive Interface (ESP32's CAN controller)
 *
 * Hardware requirements:
 *   - CAN transceiver (SN65HVD230, MCP2551, TJA1050, etc.)
 *   - TX pin connected to transceiver TXD
 *   - RX pin connected to transceiver RXD
 *
 * Default pins (AI Thinker style):
 *   - TX: GPIO 5
 *   - RX: GPIO 4
 */
class Esp32Can : public ICan {
public:
    /**
     * Constructor with optional pin configuration.
     * @param txPin GPIO for CAN TX (default from PinConfig)
     * @param rxPin GPIO for CAN RX (default from PinConfig)
     */
    Esp32Can(int txPin = CAN_TX_PIN, int rxPin = CAN_RX_PIN);

    ~Esp32Can() override;

    // ===== Lifecycle =====
    bool begin(uint32_t baudRate = 500000) override;
    void end() override;
    CanState getState() const override;
    bool recover() override;

    // ===== Transmit =====
    bool send(const CanMessage& msg, uint32_t timeoutMs = 10) override;
    bool canSend() const override;

    // ===== Receive =====
    int available() const override;
    bool receive(CanMessage& msg, uint32_t timeoutMs = 0) override;
    void setReceiveCallback(CanReceiveCallback callback) override;

    // ===== Filtering =====
    void setFilter(uint32_t filter, uint32_t mask, bool extended = false) override;
    void clearFilters() override;

    // ===== Status =====
    CanErrors getErrors() const override;
    void resetErrors() override;
    bool hasError() const override;

private:
    int txPin_;
    int rxPin_;
    uint32_t baudRate_ = 0;
    bool initialized_ = false;
    CanReceiveCallback receiveCallback_ = nullptr;

    // Error tracking
    mutable CanErrors errors_ = {};

    // Convert between ESP-IDF and HAL types
    static twai_timing_config_t getBaudConfig(uint32_t baudRate);
    static void twaiToCanMessage(const twai_message_t& twai, CanMessage& msg);
    static void canToTwaiMessage(const CanMessage& msg, twai_message_t& twai);
};

} // namespace hal

#else // !HAS_CAN

#include "../ICan.h"

namespace hal {

// Stub implementation when CAN is disabled
class Esp32Can : public ICan {
public:
    Esp32Can(int = 0, int = 0) {}
    bool begin(uint32_t = 500000) override { return false; }
    void end() override {}
    CanState getState() const override { return CanState::STOPPED; }
    bool recover() override { return false; }
    bool send(const CanMessage&, uint32_t = 10) override { return false; }
    bool canSend() const override { return false; }
    int available() const override { return 0; }
    bool receive(CanMessage&, uint32_t = 0) override { return false; }
    void setReceiveCallback(CanReceiveCallback) override {}
    void setFilter(uint32_t, uint32_t, bool = false) override {}
    void clearFilters() override {}
    CanErrors getErrors() const override { return {}; }
    void resetErrors() override {}
    bool hasError() const override { return false; }
};

} // namespace hal

#endif // HAS_CAN
