#include "module/LoggingModule.h"
#include "core/Debug.h"
#include "core/Event.h"

#include <Arduino.h>
#include <ArduinoJson.h>

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
        // Forward to host
        sendLog("info", "PING", "PING event", evt.timestamp_ms);
        break;

    case EventType::PONG:
        DBG_PRINTLN("[LOG] PONG event");
        sendLog("info", "PONG", "PONG event", evt.timestamp_ms);
        break;

    case EventType::JSON_MESSAGE_RX:
        DBG_PRINTF("[LOG] JSON RX: %s\n", evt.payload.json.c_str());
        sendLogJson("debug", "JSON_RX", evt.payload.json, evt.timestamp_ms);
        break;

    case EventType::JSON_MESSAGE_TX:
        DBG_PRINTF("[LOG] JSON TX: %s\n", evt.payload.json.c_str());
        sendLogJson("debug", "JSON_TX", evt.payload.json, evt.timestamp_ms);
        break;

    case EventType::HEARTBEAT:
        DBG_PRINTLN("[LOG] HEARTBEAT");
        // Uncomment if you want these going to host too (might be noisy):
        // sendLog("debug", "HEARTBEAT", "Heartbeat tick", evt.timestamp_ms);
        break;

    case EventType::WHOMAI_REQUEST:
        DBG_PRINTLN("[LOG] WHOAMI request");
        sendLog("info", "WHOAMI", "WHOAMI request received", evt.timestamp_ms);
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
    currentLevel_ = parseLevel(levelStr);
    DBG_PRINTF("[LOG] Level changed to %s\n", levelStr ? levelStr : "(null)");
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

// -----------------------------------------------------------------------------
// Helpers: forward logs to Python host as JSON (with level filtering)
// -----------------------------------------------------------------------------

void LoggingModule::sendLog(const char* level,
                            const char* tag,
                            const char* msg,
                            uint32_t ts_ms)
{
    // Global OFF kills everything
    if (currentLevel_ == LogLevel::OFF) {
        return;
    }

    LogLevel msgLevel = parseLevel(level);
    // If message level is "less severe" than currentLevel_, drop it
    if (msgLevel < currentLevel_) {
        return;
    }

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
    if (currentLevel_ == LogLevel::OFF) {
        return;
    }

    LogLevel msgLevel = parseLevel(level);
    if (msgLevel < currentLevel_) {
        return;
    }

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
