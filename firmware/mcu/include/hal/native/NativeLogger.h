// include/hal/native/NativeLogger.h
// Native logger implementation using stdout for testing
#pragma once

#include "../ILogger.h"
#include <cstdio>

namespace hal {

/// Native logger implementation using stdout
/// Used for unit tests and native builds
class NativeLogger : public ILogger {
public:
    NativeLogger() : level_(LogLevel::INFO) {}

    void setLevel(LogLevel level) override { level_ = level; }
    LogLevel getLevel() const override { return level_; }

    void print(const char* msg) override {
        std::fputs(msg, stdout);
    }

    void println(const char* msg) override {
        std::puts(msg);
    }

    void println() override {
        std::putchar('\n');
    }

    void printf(const char* fmt, ...) override {
        va_list args;
        va_start(args, fmt);
        std::vprintf(fmt, args);
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

        std::fputs(logLevelPrefix(level), stdout);
        std::vprintf(fmt, args);
        std::putchar('\n');
    }

private:
    LogLevel level_;
};

} // namespace hal
