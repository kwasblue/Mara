// src/hal/linux/LinuxLogger.cpp
// Linux logger implementation supporting stdout, syslog, and file output

#include "hal/linux/LinuxLogger.h"

#if PLATFORM_LINUX

#include <syslog.h>
#include <ctime>
#include <cstdio>
#include <cstring>

namespace hal {

LinuxLogger::LinuxLogger() : level_(LogLevel::INFO), output_(LinuxLogOutput::Stdout) {}

LinuxLogger::~LinuxLogger() {
    if (syslogOpen_) {
        closelog();
    }
    if (logFile_) {
        fclose(logFile_);
    }
}

void LinuxLogger::setLevel(LogLevel level) {
    std::lock_guard<std::mutex> lock(mutex_);
    level_ = level;
}

LogLevel LinuxLogger::getLevel() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return level_;
}

void LinuxLogger::setOutput(LinuxLogOutput output, const char* param) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Close existing output
    if (syslogOpen_) {
        closelog();
        syslogOpen_ = false;
    }
    if (logFile_) {
        fclose(logFile_);
        logFile_ = nullptr;
    }

    output_ = output;

    switch (output) {
        case LinuxLogOutput::Syslog:
            if (param) {
                strncpy(syslogIdent_, param, sizeof(syslogIdent_) - 1);
            } else {
                strcpy(syslogIdent_, "mara");
            }
            openlog(syslogIdent_, LOG_PID | LOG_NDELAY, LOG_USER);
            syslogOpen_ = true;
            break;

        case LinuxLogOutput::File:
            if (param) {
                logFile_ = fopen(param, "a");
            }
            break;

        default:
            break;
    }
}

void LinuxLogger::setTimestamps(bool enable) {
    std::lock_guard<std::mutex> lock(mutex_);
    timestamps_ = enable;
}

void LinuxLogger::print(const char* msg) {
    std::lock_guard<std::mutex> lock(mutex_);
    writeOutput(msg);
}

void LinuxLogger::println(const char* msg) {
    std::lock_guard<std::mutex> lock(mutex_);
    writeOutput(msg);
    writeOutput("\n");
}

void LinuxLogger::println() {
    std::lock_guard<std::mutex> lock(mutex_);
    writeOutput("\n");
}

void LinuxLogger::printf(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);

    char buf[512];
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    std::lock_guard<std::mutex> lock(mutex_);
    writeOutput(buf);
}

void LinuxLogger::log(LogLevel level, const char* fmt, ...) {
    if (level < level_) return;

    va_list args;
    va_start(args, fmt);
    vlog(level, fmt, args);
    va_end(args);
}

void LinuxLogger::vlog(LogLevel level, const char* fmt, va_list args) {
    if (level < level_) return;

    std::lock_guard<std::mutex> lock(mutex_);

    if (output_ == LinuxLogOutput::Syslog) {
        // Use syslog directly
        vsyslog(logLevelToSyslog(level), fmt, args);
        return;
    }

    // Format message
    char msgBuf[512];
    vsnprintf(msgBuf, sizeof(msgBuf), fmt, args);

    // Build output with optional timestamp and level prefix
    if (timestamps_) {
        writeTimestamp();
    }

    writeOutput(logLevelPrefix(level));
    writeOutput(msgBuf);
    writeOutput("\n");

    // Flush file output
    if (logFile_) {
        fflush(logFile_);
    }
}

void LinuxLogger::writeOutput(const char* msg) {
    switch (output_) {
        case LinuxLogOutput::Stdout:
            fputs(msg, stdout);
            break;
        case LinuxLogOutput::File:
            if (logFile_) {
                fputs(msg, logFile_);
            }
            break;
        case LinuxLogOutput::Syslog:
            // Syslog handled separately in vlog
            break;
    }
}

void LinuxLogger::writeTimestamp() {
    time_t now = time(nullptr);
    struct tm* tm_info = localtime(&now);

    char timeBuf[32];
    strftime(timeBuf, sizeof(timeBuf), "[%H:%M:%S] ", tm_info);
    writeOutput(timeBuf);
}

int LinuxLogger::logLevelToSyslog(LogLevel level) {
    switch (level) {
        case LogLevel::TRACE:
        case LogLevel::DEBUG:
            return LOG_DEBUG;
        case LogLevel::INFO:
            return LOG_INFO;
        case LogLevel::WARN:
            return LOG_WARNING;
        case LogLevel::ERROR:
            return LOG_ERR;
        default:
            return LOG_INFO;
    }
}

} // namespace hal

#endif // PLATFORM_LINUX
