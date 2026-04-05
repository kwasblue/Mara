// include/hal/linux/LinuxLogger.h
// Linux logger implementation supporting stdout, syslog, and file output
#pragma once

#include "../ILogger.h"
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <mutex>

namespace hal {

/// Log output destination
enum class LinuxLogOutput : uint8_t {
    Stdout,     // Standard output (default)
    Syslog,     // System log (/var/log/syslog or journald)
    File        // Log to file
};

/// Linux logger implementation
///
/// Provides logging to stdout, syslog, or file.
/// Thread-safe via internal mutex.
///
/// Usage:
///   LinuxLogger logger;
///   logger.setOutput(LinuxLogOutput::Syslog, "mara");
///   logger.info("System started");
class LinuxLogger : public ILogger {
public:
    /// Constructor (defaults to stdout)
    LinuxLogger();

    /// Destructor (closes syslog/file if open)
    ~LinuxLogger();

    void setLevel(LogLevel level) override;
    LogLevel getLevel() const override;

    void print(const char* msg) override;
    void println(const char* msg) override;
    void println() override;
    void printf(const char* fmt, ...) override;
    void log(LogLevel level, const char* fmt, ...) override;

    /// Set output destination
    /// @param output Output type (Stdout, Syslog, File)
    /// @param param For Syslog: ident string; for File: file path
    void setOutput(LinuxLogOutput output, const char* param = nullptr);

    /// Include timestamps in log messages
    void setTimestamps(bool enable);

protected:
    void vlog(LogLevel level, const char* fmt, va_list args) override;

private:
    LogLevel level_ = LogLevel::INFO;
    LinuxLogOutput output_ = LinuxLogOutput::Stdout;
    FILE* logFile_ = nullptr;
    bool timestamps_ = true;
    bool syslogOpen_ = false;
    char syslogIdent_[32] = {0};
    mutable std::mutex mutex_;

    void writeOutput(const char* msg);
    void writeTimestamp();
    int logLevelToSyslog(LogLevel level);
};

} // namespace hal
