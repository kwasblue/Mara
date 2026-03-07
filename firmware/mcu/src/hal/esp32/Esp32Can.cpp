#include "hal/esp32/Esp32Can.h"

#if HAS_CAN

#include "utils/Logger.h"
#include <Arduino.h>

static const char* TAG = "CAN";

namespace hal {

Esp32Can::Esp32Can(int txPin, int rxPin)
    : txPin_(txPin), rxPin_(rxPin) {}

Esp32Can::~Esp32Can() {
    end();
}

bool Esp32Can::begin(uint32_t baudRate) {
    if (initialized_) {
        LOG_WARN(TAG, "Already initialized");
        return true;
    }

    baudRate_ = baudRate;

    // General configuration
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
        static_cast<gpio_num_t>(txPin_),
        static_cast<gpio_num_t>(rxPin_),
        TWAI_MODE_NORMAL
    );
    g_config.rx_queue_len = 32;
    g_config.tx_queue_len = 16;

    // Timing configuration
    twai_timing_config_t t_config = getBaudConfig(baudRate);

    // Filter configuration (accept all by default)
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    // Install driver
    esp_err_t err = twai_driver_install(&g_config, &t_config, &f_config);
    if (err != ESP_OK) {
        LOG_ERROR(TAG, "Driver install failed: %d", err);
        return false;
    }

    // Start driver
    err = twai_start();
    if (err != ESP_OK) {
        LOG_ERROR(TAG, "Start failed: %d", err);
        twai_driver_uninstall();
        return false;
    }

    initialized_ = true;
    LOG_INFO(TAG, "Initialized at %u bps (TX:%d, RX:%d)", baudRate, txPin_, rxPin_);
    return true;
}

void Esp32Can::end() {
    if (!initialized_) return;

    twai_stop();
    twai_driver_uninstall();
    initialized_ = false;
    LOG_INFO(TAG, "Stopped");
}

CanState Esp32Can::getState() const {
    if (!initialized_) return CanState::STOPPED;

    twai_status_info_t status;
    if (twai_get_status_info(&status) != ESP_OK) {
        return CanState::STOPPED;
    }

    switch (status.state) {
        case TWAI_STATE_STOPPED:
            return CanState::STOPPED;
        case TWAI_STATE_RUNNING:
            return CanState::RUNNING;
        case TWAI_STATE_BUS_OFF:
            return CanState::BUS_OFF;
        case TWAI_STATE_RECOVERING:
            return CanState::RECOVERING;
        default:
            return CanState::STOPPED;
    }
}

bool Esp32Can::recover() {
    if (!initialized_) return false;

    esp_err_t err = twai_initiate_recovery();
    if (err == ESP_OK) {
        LOG_INFO(TAG, "Recovery initiated");
        return true;
    }

    LOG_WARN(TAG, "Recovery failed: %d", err);
    return false;
}

bool Esp32Can::send(const CanMessage& msg, uint32_t timeoutMs) {
    if (!initialized_) return false;

    twai_message_t twaiMsg;
    canToTwaiMessage(msg, twaiMsg);

    TickType_t ticks = (timeoutMs == 0) ? 0 : pdMS_TO_TICKS(timeoutMs);
    esp_err_t err = twai_transmit(&twaiMsg, ticks);

    if (err != ESP_OK) {
        errors_.txErrors++;
        if (err == TWAI_ERR_TX_ARB_LOST) {
            errors_.arbitrationLost++;
        }
        return false;
    }

    return true;
}

bool Esp32Can::canSend() const {
    if (!initialized_) return false;

    twai_status_info_t status;
    if (twai_get_status_info(&status) != ESP_OK) {
        return false;
    }

    return status.msgs_to_tx < 16;  // TX queue not full
}

int Esp32Can::available() const {
    if (!initialized_) return 0;

    twai_status_info_t status;
    if (twai_get_status_info(&status) != ESP_OK) {
        return 0;
    }

    return status.msgs_to_rx;
}

bool Esp32Can::receive(CanMessage& msg, uint32_t timeoutMs) {
    if (!initialized_) return false;

    twai_message_t twaiMsg;
    TickType_t ticks = (timeoutMs == 0) ? 0 : pdMS_TO_TICKS(timeoutMs);

    esp_err_t err = twai_receive(&twaiMsg, ticks);
    if (err != ESP_OK) {
        if (err != ESP_ERR_TIMEOUT) {
            errors_.rxErrors++;
        }
        return false;
    }

    twaiToCanMessage(twaiMsg, msg);

    // Call callback if set
    if (receiveCallback_) {
        receiveCallback_(msg);
    }

    return true;
}

void Esp32Can::setReceiveCallback(CanReceiveCallback callback) {
    receiveCallback_ = callback;
}

void Esp32Can::setFilter(uint32_t filter, uint32_t mask, bool extended) {
    if (!initialized_) return;

    // Must stop and restart to change filters
    twai_stop();

    twai_filter_config_t f_config;
    if (extended) {
        f_config.acceptance_code = filter << 3;
        f_config.acceptance_mask = ~(mask << 3);
        f_config.single_filter = true;
    } else {
        f_config.acceptance_code = filter << 21;
        f_config.acceptance_mask = ~(mask << 21);
        f_config.single_filter = true;
    }

    // Reinstall with new filter
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
        static_cast<gpio_num_t>(txPin_),
        static_cast<gpio_num_t>(rxPin_),
        TWAI_MODE_NORMAL
    );
    g_config.rx_queue_len = 32;
    g_config.tx_queue_len = 16;

    twai_timing_config_t t_config = getBaudConfig(baudRate_);

    twai_driver_uninstall();
    twai_driver_install(&g_config, &t_config, &f_config);
    twai_start();

    LOG_DEBUG(TAG, "Filter set: 0x%08X mask 0x%08X", filter, mask);
}

void Esp32Can::clearFilters() {
    if (!initialized_) return;

    twai_stop();

    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
        static_cast<gpio_num_t>(txPin_),
        static_cast<gpio_num_t>(rxPin_),
        TWAI_MODE_NORMAL
    );
    g_config.rx_queue_len = 32;
    g_config.tx_queue_len = 16;

    twai_timing_config_t t_config = getBaudConfig(baudRate_);

    twai_driver_uninstall();
    twai_driver_install(&g_config, &t_config, &f_config);
    twai_start();

    LOG_DEBUG(TAG, "Filters cleared");
}

CanErrors Esp32Can::getErrors() const {
    return errors_;
}

void Esp32Can::resetErrors() {
    errors_ = {};
}

bool Esp32Can::hasError() const {
    if (!initialized_) return true;

    CanState state = getState();
    return state == CanState::BUS_OFF || state == CanState::RECOVERING;
}

// ===== Private Helpers =====

twai_timing_config_t Esp32Can::getBaudConfig(uint32_t baudRate) {
    switch (baudRate) {
        case 1000000:
            return TWAI_TIMING_CONFIG_1MBITS();
        case 800000:
            return TWAI_TIMING_CONFIG_800KBITS();
        case 500000:
            return TWAI_TIMING_CONFIG_500KBITS();
        case 250000:
            return TWAI_TIMING_CONFIG_250KBITS();
        case 125000:
            return TWAI_TIMING_CONFIG_125KBITS();
        case 100000:
            return TWAI_TIMING_CONFIG_100KBITS();
        case 50000:
            return TWAI_TIMING_CONFIG_50KBITS();
        case 25000:
            return TWAI_TIMING_CONFIG_25KBITS();
        default:
            LOG_WARN(TAG, "Unsupported baud %u, using 500kbps", baudRate);
            return TWAI_TIMING_CONFIG_500KBITS();
    }
}

void Esp32Can::twaiToCanMessage(const twai_message_t& twai, CanMessage& msg) {
    msg.id = twai.identifier;
    msg.len = twai.data_length_code;
    msg.extended = twai.extd;
    msg.rtr = twai.rtr;
    for (int i = 0; i < 8; i++) {
        msg.data[i] = twai.data[i];
    }
}

void Esp32Can::canToTwaiMessage(const CanMessage& msg, twai_message_t& twai) {
    twai.identifier = msg.id;
    twai.data_length_code = msg.len;
    twai.extd = msg.extended ? 1 : 0;
    twai.rtr = msg.rtr ? 1 : 0;
    twai.ss = 1;  // Single shot mode
    for (int i = 0; i < 8; i++) {
        twai.data[i] = msg.data[i];
    }
}

} // namespace hal

#endif // HAS_CAN
