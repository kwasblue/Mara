// include/hal/esp32/Esp32Logger.h
// ESP32 logger implementation using Arduino Serial
#pragma once

#include "../ILogger.h"
#include <Arduino.h>

namespace hal {

/// ESP32 logger implementation wrapping Arduino Serial
class Esp32Logger : public ILogger {
public:
    explicit Esp32Logger(HardwareSerial& serial = Serial)
        : serial_(serial), level_(LogLevel::INFO) {}

    void setLevel(LogLevel level) override { level_ = level; }
    LogLevel getLevel() const override { return level_; }

    void print(const char* msg) override {
        serial_.print(msg);
    }

    void println(const char* msg) override {
        serial_.println(msg);
    }

    void println() override {
        serial_.println();
    }

    void printf(const char* fmt, ...) override {
        va_list args;
        va_start(args, fmt);
        vprintf_impl(fmt, args);
        va_end(args);
    }

    void log(LogLevel level, const char* fmt, ...) override {
        if (level < level_) return;

        va_list args;
        va_start(args, fmt);
        vlog(level, fmt, args);
        va_end(args);
    }

protected:
    void vlog(LogLevel level, const char* fmt, va_list args) override {
        if (level < level_) return;

        serial_.print(logLevelPrefix(level));
        vprintf_impl(fmt, args);
        serial_.println();
    }

private:
    void vprintf_impl(const char* fmt, va_list args) {
        char buf[256];
        vsnprintf(buf, sizeof(buf), fmt, args);
        serial_.print(buf);
    }

    HardwareSerial& serial_;
    LogLevel level_;
};

} // namespace hal
