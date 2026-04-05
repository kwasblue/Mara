// src/hal/linux/LinuxGpio.cpp
// Linux GPIO implementation using libgpiod

#include "hal/linux/LinuxGpio.h"

#if PLATFORM_LINUX && HAS_LIBGPIOD

#include <gpiod.h>
#include <cstring>
#include <stdexcept>

namespace hal {

LinuxGpio::LinuxGpio(const char* chipPath) {
    strncpy(chipPath_, chipPath, sizeof(chipPath_) - 1);
    chipPath_[sizeof(chipPath_) - 1] = '\0';
}

LinuxGpio::~LinuxGpio() {
    end();
}

bool LinuxGpio::begin() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (chip_) {
        return true;  // Already initialized
    }

    chip_ = gpiod_chip_open(chipPath_);
    return chip_ != nullptr;
}

void LinuxGpio::end() {
    std::lock_guard<std::mutex> lock(mutex_);

    // Release all lines
    for (auto& [pin, state] : pins_) {
        if (state.intThread) {
            state.intRunning = false;
            if (state.intThread->joinable()) {
                state.intThread->join();
            }
            delete state.intThread;
        }
        releaseLine(pin);
    }
    pins_.clear();

    if (chip_) {
        gpiod_chip_close(chip_);
        chip_ = nullptr;
    }
}

void LinuxGpio::pinMode(uint8_t pin, PinMode mode) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Release existing line if any
    releaseLine(pin);

    // Request new line with mode
    requestLine(pin, mode);

    pins_[pin].mode = mode;
}

void LinuxGpio::digitalWrite(uint8_t pin, uint8_t value) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = pins_.find(pin);
    if (it == pins_.end() || !it->second.request) {
        return;
    }

    gpiod_line_request_set_value(it->second.request, pin, value ? GPIOD_LINE_VALUE_ACTIVE : GPIOD_LINE_VALUE_INACTIVE);
    it->second.value = value;
}

int LinuxGpio::digitalRead(uint8_t pin) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = pins_.find(pin);
    if (it == pins_.end() || !it->second.request) {
        return 0;
    }

    enum gpiod_line_value val = gpiod_line_request_get_value(it->second.request, pin);
    return (val == GPIOD_LINE_VALUE_ACTIVE) ? 1 : 0;
}

void LinuxGpio::toggle(uint8_t pin) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = pins_.find(pin);
    if (it == pins_.end() || !it->second.request) {
        return;
    }

    uint8_t newVal = it->second.value ? 0 : 1;
    gpiod_line_request_set_value(it->second.request, pin, newVal ? GPIOD_LINE_VALUE_ACTIVE : GPIOD_LINE_VALUE_INACTIVE);
    it->second.value = newVal;
}

void LinuxGpio::attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Detach existing interrupt
    detachInterrupt(pin);

    auto& state = pins_[pin];
    state.isr = isr;
    state.intMode = mode;

    // TODO: Set up edge detection and interrupt thread
    // This requires reconfiguring the line with edge detection
}

void LinuxGpio::detachInterrupt(uint8_t pin) {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = pins_.find(pin);
    if (it == pins_.end()) {
        return;
    }

    auto& state = it->second;
    if (state.intThread) {
        state.intRunning = false;
        if (state.intThread->joinable()) {
            state.intThread->join();
        }
        delete state.intThread;
        state.intThread = nullptr;
    }

    state.isr = nullptr;
    state.intMode = InterruptMode::Disabled;
}

void LinuxGpio::disableInterrupts() {
    interruptsEnabled_ = false;
}

void LinuxGpio::enableInterrupts() {
    interruptsEnabled_ = true;
}

void LinuxGpio::releaseLine(uint8_t pin) {
    auto it = pins_.find(pin);
    if (it != pins_.end() && it->second.request) {
        gpiod_line_request_release(it->second.request);
        it->second.request = nullptr;
    }
}

bool LinuxGpio::requestLine(uint8_t pin, PinMode mode) {
    if (!chip_) {
        return false;
    }

    gpiod_line_settings* settings = gpiod_line_settings_new();
    if (!settings) {
        return false;
    }

    // Configure direction
    if (mode == PinMode::Output || mode == PinMode::OpenDrain) {
        gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_OUTPUT);
    } else {
        gpiod_line_settings_set_direction(settings, GPIOD_LINE_DIRECTION_INPUT);
    }

    // Configure bias
    switch (mode) {
        case PinMode::InputPullup:
            gpiod_line_settings_set_bias(settings, GPIOD_LINE_BIAS_PULL_UP);
            break;
        case PinMode::InputPulldown:
            gpiod_line_settings_set_bias(settings, GPIOD_LINE_BIAS_PULL_DOWN);
            break;
        case PinMode::OpenDrain:
            gpiod_line_settings_set_drive(settings, GPIOD_LINE_DRIVE_OPEN_DRAIN);
            break;
        default:
            gpiod_line_settings_set_bias(settings, GPIOD_LINE_BIAS_DISABLED);
            break;
    }

    // Create line config
    gpiod_line_config* line_config = gpiod_line_config_new();
    if (!line_config) {
        gpiod_line_settings_free(settings);
        return false;
    }

    unsigned int offset = pin;
    gpiod_line_config_add_line_settings(line_config, &offset, 1, settings);

    // Create request config
    gpiod_request_config* req_config = gpiod_request_config_new();
    if (!req_config) {
        gpiod_line_config_free(line_config);
        gpiod_line_settings_free(settings);
        return false;
    }

    gpiod_request_config_set_consumer(req_config, "mara");

    // Request lines
    gpiod_line_request* request = gpiod_chip_request_lines(chip_, req_config, line_config);

    gpiod_request_config_free(req_config);
    gpiod_line_config_free(line_config);
    gpiod_line_settings_free(settings);

    if (!request) {
        return false;
    }

    pins_[pin].request = request;
    return true;
}

} // namespace hal

#else // !HAS_LIBGPIOD - Stub implementation

namespace hal {

LinuxGpio::LinuxGpio(const char* chipPath) {
    strncpy(chipPath_, chipPath, sizeof(chipPath_) - 1);
}

LinuxGpio::~LinuxGpio() { end(); }
bool LinuxGpio::begin() { return true; }
void LinuxGpio::end() {}
void LinuxGpio::pinMode(uint8_t pin, PinMode mode) { (void)pin; (void)mode; }
void LinuxGpio::digitalWrite(uint8_t pin, uint8_t value) { (void)pin; (void)value; }
int LinuxGpio::digitalRead(uint8_t pin) { (void)pin; return 0; }
void LinuxGpio::toggle(uint8_t pin) { (void)pin; }
void LinuxGpio::attachInterrupt(uint8_t pin, void (*isr)(), InterruptMode mode) { (void)pin; (void)isr; (void)mode; }
void LinuxGpio::detachInterrupt(uint8_t pin) { (void)pin; }
void LinuxGpio::disableInterrupts() {}
void LinuxGpio::enableInterrupts() {}
void LinuxGpio::releaseLine(uint8_t pin) { (void)pin; }
bool LinuxGpio::requestLine(uint8_t pin, PinMode mode) { (void)pin; (void)mode; return true; }

} // namespace hal

#endif // HAS_LIBGPIOD
