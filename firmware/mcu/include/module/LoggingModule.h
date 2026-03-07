#pragma once

#include <string>
#include <cstdint>

#include "core/EventBus.h"
#include "core/Event.h"
#include "core/IModule.h"

class LoggingModule : public IModule {
public:
    enum class LogLevel : uint8_t {
        DEBUG = 0,
        INFO  = 1,
        WARN  = 2,
        ERROR = 3,
        OFF   = 4
    };

    explicit LoggingModule(EventBus& bus)
        : bus_(bus)
        , currentLevel_(LogLevel::INFO)  // default verbosity
    {}

    // IModule interface
    void setup() override;
    void loop(uint32_t now_ms) override;
    void handleEvent(const Event& evt) override;   // ✅ add override

    static void onEventStatic(const Event& evt);

    // Access to singleton instance
    static LoggingModule* instance() { return s_instance; }

    // Remote-controlled log level (from CommandHandler)
    void setLogLevel(const char* levelStr);
    LogLevel currentLevel() const { return currentLevel_; }
    const char* name() const override { return "LoggingModule"; }

private:
    LogLevel parseLevel(const char* s) const;

    // Forward logs to Python host as JSON
    void sendLog(const char* level,
                 const char* tag,
                 const char* msg,
                 uint32_t ts_ms);

    void sendLogJson(const char* level,
                     const char* tag,
                     const std::string& json,
                     uint32_t ts_ms);

    EventBus&      bus_;
    static LoggingModule* s_instance;
    LogLevel       currentLevel_;
};
