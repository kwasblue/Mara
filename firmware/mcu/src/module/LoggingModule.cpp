#include "module/LoggingModule.h"
#include "core/Debug.h"
#include "core/Event.h"
#include "core/Clock.h"

#include <ArduinoJson.h>
#include <cstdarg>
#include <cstdio>

LoggingModule* LoggingModule::s_instance = nullptr;

void LoggingModule::setup() {
    s_instance = this;
    bus_.subscribe(&LoggingModule::onEventStatic);

    DBG_PRINTLN("[LoggingModule] setup complete");
}

void LoggingModule::loop(uint32_t /*now_ms*/) {
    // If you want periodic flushing or timed logs, add here.
}

void LoggingModule::onEventStatic(const Event& evt) {
    if (s_instance) {
        s_instance->handleEvent(evt);
    }
}

void LoggingModule::handleEvent(const Event& evt) {

    switch (evt.type) {

    case EventType::PING:
        // Local debug
        DBG_PRINTLN("[LOG] PING event");
        // Forward to host (uses subsystem logging now)
        doLog("system", LogLevel::INFO, "PING event");
        break;

    case EventType::PONG:
        DBG_PRINTLN("[LOG] PONG event");
        doLog("system", LogLevel::INFO, "PONG event");
        break;

    case EventType::JSON_MESSAGE_RX:
        // Raw JSON payload echoing is extremely expensive at high verbosity and can
        // destabilize the control/transport path. Keep a lightweight local trace only.
        DBG_PRINTF("[LOG] JSON RX (%u bytes)\n", (unsigned)evt.payload.json.size());
        break;

    case EventType::JSON_MESSAGE_TX:
        // Never forward JSON TX as another JSON log event: that creates recursive
        // amplification because sendLog()/sendLogJson() themselves publish JSON_MESSAGE_TX.
        // Keep a lightweight local trace only.
        DBG_PRINTF("[LOG] JSON TX (%u bytes)\n", (unsigned)evt.payload.json.size());
        break;

    case EventType::HEARTBEAT:
        DBG_PRINTLN("[LOG] HEARTBEAT");
        // Uncomment if you want these going to host too (might be noisy):
        // doLog("system", LogLevel::DEBUG, "Heartbeat tick");
        break;

    case EventType::WHOMAI_REQUEST:
        DBG_PRINTLN("[LOG] WHOAMI request");
        doLog("system", LogLevel::INFO, "WHOAMI request received");
        break;

    default:
        // OPTIONAL: log unknown or unhandled events
        // DBG_PRINTF("[LOG] event type=%d\n", (int)evt.type);
        break;
    }
}

// -----------------------------------------------------------------------------
// Log level control
// -----------------------------------------------------------------------------

void LoggingModule::setLogLevel(const char* levelStr) {
    globalLevel_ = parseLevel(levelStr);
    DBG_PRINTF("[LOG] Global level changed to %s\n", levelStr ? levelStr : "(null)");
}

void LoggingModule::setSubsystemLevel(const char* subsystem, const char* levelStr) {
    if (!subsystem) return;

    LogLevel level = parseLevel(levelStr);

    if (level == LogLevel::OFF) {
        // OFF means use global level (remove override)
        subsystemLevels_.erase(subsystem);
        DBG_PRINTF("[LOG] Subsystem '%s' level cleared (using global)\n", subsystem);
    } else {
        subsystemLevels_[subsystem] = level;
        DBG_PRINTF("[LOG] Subsystem '%s' level set to %s\n", subsystem, levelStr);
    }
}

LoggingModule::LogLevel LoggingModule::getEffectiveLevel(const char* subsystem) const {
    if (subsystem) {
        auto it = subsystemLevels_.find(subsystem);
        if (it != subsystemLevels_.end()) {
            return it->second;
        }
    }
    return globalLevel_;
}

void LoggingModule::clearSubsystemLevels() {
    subsystemLevels_.clear();
    DBG_PRINTLN("[LOG] All subsystem levels cleared");
}

std::string LoggingModule::getSubsystemLevelsJson() const {
    JsonDocument doc;
    doc["global"] = levelToString(globalLevel_);

    JsonObject subsystems = doc["subsystems"].to<JsonObject>();
    for (const auto& kv : subsystemLevels_) {
        subsystems[kv.first] = levelToString(kv.second);
    }

    std::string out;
    serializeJson(doc, out);
    return out;
}

LoggingModule::LogLevel LoggingModule::parseLevel(const char* s) const {
    if (!s) return LogLevel::INFO;

    if (strcmp(s, "debug") == 0) return LogLevel::DEBUG;
    if (strcmp(s, "info")  == 0) return LogLevel::INFO;
    if (strcmp(s, "warn")  == 0) return LogLevel::WARN;
    if (strcmp(s, "error") == 0) return LogLevel::ERROR;
    if (strcmp(s, "off")   == 0) return LogLevel::OFF;

    return LogLevel::INFO;
}

const char* LoggingModule::levelToString(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG: return "debug";
        case LogLevel::INFO:  return "info";
        case LogLevel::WARN:  return "warn";
        case LogLevel::ERROR: return "error";
        case LogLevel::OFF:   return "off";
        default:              return "unknown";
    }
}

// -----------------------------------------------------------------------------
// Static logging API
// -----------------------------------------------------------------------------

bool LoggingModule::wouldLog(const char* subsystem, LogLevel level) {
    if (!s_instance) return false;
    LogLevel effective = s_instance->getEffectiveLevel(subsystem);
    return level >= effective && effective != LogLevel::OFF;
}

void LoggingModule::log(const char* subsystem, LogLevel level, const char* fmt, ...) {
    if (!s_instance) return;
    if (!wouldLog(subsystem, level)) return;

    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    s_instance->doLog(subsystem, level, buf);
}

void LoggingModule::logDebug(const char* subsystem, const char* fmt, ...) {
    if (!s_instance) return;
    if (!wouldLog(subsystem, LogLevel::DEBUG)) return;

    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    s_instance->doLog(subsystem, LogLevel::DEBUG, buf);
}

void LoggingModule::logInfo(const char* subsystem, const char* fmt, ...) {
    if (!s_instance) return;
    if (!wouldLog(subsystem, LogLevel::INFO)) return;

    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    s_instance->doLog(subsystem, LogLevel::INFO, buf);
}

void LoggingModule::logWarn(const char* subsystem, const char* fmt, ...) {
    if (!s_instance) return;
    if (!wouldLog(subsystem, LogLevel::WARN)) return;

    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    s_instance->doLog(subsystem, LogLevel::WARN, buf);
}

void LoggingModule::logError(const char* subsystem, const char* fmt, ...) {
    if (!s_instance) return;
    if (!wouldLog(subsystem, LogLevel::ERROR)) return;

    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    s_instance->doLog(subsystem, LogLevel::ERROR, buf);
}

// -----------------------------------------------------------------------------
// Internal implementation
// -----------------------------------------------------------------------------

void LoggingModule::doLog(const char* subsystem, LogLevel level, const char* msg) {
    // Also output to local serial for debugging
    DBG_PRINTF("[%s] %s: %s\n",
        subsystem ? subsystem : "?",
        levelToString(level),
        msg);

    // Send to host
    sendLog(levelToString(level), subsystem, msg, mara::getSystemClock().millis());
}

void LoggingModule::sendLog(const char* level,
                            const char* tag,
                            const char* msg,
                            uint32_t ts_ms)
{
    // Note: Level filtering is done in doLog/wouldLog, not here
    // This allows direct sendLog calls to bypass filtering if needed

    using namespace ArduinoJson;

    JsonDocument doc;  // dynamic doc (ArduinoJson v7 style)

    doc["src"]  = "mcu";
    doc["type"] = "LOG";

    JsonObject log = doc["log"].to<JsonObject>();
    log["level"]  = level;
    log["tag"]    = tag;
    log["msg"]    = msg;
    log["ts_ms"]  = ts_ms;

    std::string out;
    serializeJson(doc, out);

    Event logEvt;
    logEvt.type         = EventType::JSON_MESSAGE_TX;
    logEvt.timestamp_ms = ts_ms;
    logEvt.payload      = {};
    logEvt.payload.json = std::move(out);

    bus_.publish(logEvt);
}

void LoggingModule::sendLogJson(const char* level,
                                const char* tag,
                                const std::string& json,
                                uint32_t ts_ms)
{
    using namespace ArduinoJson;

    JsonDocument doc;  // dynamic doc

    doc["src"]  = "mcu";
    doc["type"] = "LOG";

    JsonObject log = doc["log"].to<JsonObject>();
    log["level"]  = level;
    log["tag"]    = tag;
    log["msg"]    = "JSON message";
    log["ts_ms"]  = ts_ms;
    log["raw"]    = json;

    std::string out;
    serializeJson(doc, out);

    Event logEvt;
    logEvt.type         = EventType::JSON_MESSAGE_TX;
    logEvt.timestamp_ms = ts_ms;
    logEvt.payload      = {};
    logEvt.payload.json = std::move(out);

    bus_.publish(logEvt);
}
