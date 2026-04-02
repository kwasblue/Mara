// src/core/MqttTransport.cpp

#include "config/FeatureFlags.h"

#if HAS_MQTT_TRANSPORT && HAS_WIFI

#include "transport/MqttTransport.h"
#include "config/Version.h"
#include "core/Protocol.h"
#include "core/Clock.h"
#include <ArduinoJson.h>

#if HAS_FREERTOS
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#endif

MqttTransport::MqttTransport(
    const char* broker,
    uint16_t port,
    const char* robotId,
    const char* username,
    const char* password
) :
    mqtt_(wifi_),
    broker_(broker),
    port_(port),
    robotId_(robotId),
    username_(username ? username : ""),
    password_(password ? password : "")
{
    topicCmd_       = "mara/" + robotId_ + "/cmd";
    topicAck_       = "mara/" + robotId_ + "/ack";
    topicTelemetry_ = "mara/" + robotId_ + "/telemetry";
    topicState_     = "mara/" + robotId_ + "/state";
    topicDiscovery_ = "mara/fleet/discover";

    // Create mutex for thread-safe mqtt_ access
    mqttMutex_ = xSemaphoreCreateMutex();
}

MqttTransport::~MqttTransport() {
    if (mqttMutex_) {
        vSemaphoreDelete(mqttMutex_);
        mqttMutex_ = nullptr;
    }
}

void MqttTransport::begin() {
    mqtt_.setServer(broker_.c_str(), port_);
    mqtt_.setBufferSize(1024);
    mqtt_.setKeepAlive(5);
    mqtt_.setSocketTimeout(1);

    mqtt_.setCallback([this](char* topic, uint8_t* payload, unsigned int length) {
        this->onMessage(topic, payload, length);
    });

    nextReconnectAttemptMs_ = mara::getSystemClock().millis();
}

void MqttTransport::loop() {
    // Don't access mqtt_ while connect task is running
    if (connectInProgress_) {
        return;
    }

    // Take mutex to safely access mqtt_
    if (mqttMutex_ && xSemaphoreTake(mqttMutex_, pdMS_TO_TICKS(10)) == pdTRUE) {
        if (mqtt_.connected()) {
            consecutiveFailures_ = 0;
            mqtt_.loop();
            xSemaphoreGive(mqttMutex_);
            return;
        }
        xSemaphoreGive(mqttMutex_);
    } else {
        // Couldn't acquire mutex, skip this iteration
        return;
    }

    if (WiFi.status() != WL_CONNECTED) {
        return;
    }

    if (retriesExhausted()) {
        return;
    }

    uint32_t now = mara::getSystemClock().millis();
    if (now < nextReconnectAttemptMs_) {
        return;
    }

    reconnect();
}

void MqttTransport::reconnect() {
    if (mqtt_.connected() || connectInProgress_) return;

    connectInProgress_ = true;

    // Use HAL if available
    if (halScheduler_) {
        hal::TaskConfig config;
        config.name = "mqtt_connect";
        config.stackSize = 4096;
        config.priority = 1;
        config.core = 0;

        if (!halScheduler_->createTask(&MqttTransport::connectTaskEntry, this, config, halConnectTask_)) {
            connectInProgress_ = false;
            halConnectTask_.native = nullptr;
            consecutiveFailures_++;
            if (retriesExhausted()) {
                nextReconnectAttemptMs_ = UINT32_MAX;
                Serial.printf("[MQTT] Failed to start connect task (HAL); giving up after %u attempts\n",
                    static_cast<unsigned>(MAX_RETRIES));
            } else {
                nextReconnectAttemptMs_ = mara::getSystemClock().millis() + nextReconnectDelayMs();
                Serial.println("[MQTT] Failed to start connect task (HAL); backing off");
            }
        }
        return;
    }

#if HAS_FREERTOS
    // Direct FreeRTOS path (legacy fallback)
    BaseType_t ok = xTaskCreatePinnedToCore(
        &MqttTransport::connectTaskEntry,
        "mqtt_connect",
        4096,
        this,
        1,
        &connectTask_,
        0
    );

    if (ok != pdPASS) {
        connectInProgress_ = false;
        connectTask_ = nullptr;
        consecutiveFailures_++;
        if (retriesExhausted()) {
            nextReconnectAttemptMs_ = UINT32_MAX;
            Serial.printf("[MQTT] Failed to start connect task; giving up after %u attempts\n",
                static_cast<unsigned>(MAX_RETRIES));
        } else {
            nextReconnectAttemptMs_ = mara::getSystemClock().millis() + nextReconnectDelayMs();
            Serial.println("[MQTT] Failed to start connect task; backing off");
        }
    }
#else
    // No scheduler available - cannot start async connect
    connectInProgress_ = false;
    Serial.println("[MQTT] No task scheduler available for async connect");
#endif
}

void MqttTransport::connectTaskEntry(void* arg) {
    auto* self = static_cast<MqttTransport*>(arg);
    self->connectTaskBody();
}

void MqttTransport::connectTaskBody() {
    Serial.printf("[MQTT] Connecting to %s:%d as %s...\n",
        broker_.c_str(), port_, robotId_.c_str());

    const uint32_t startMs = mara::getSystemClock().millis();

    // Take mutex for all mqtt_ operations
    bool connected = false;
    bool gotMutex = mqttMutex_ && xSemaphoreTake(mqttMutex_, pdMS_TO_TICKS(5000)) == pdTRUE;

    if (gotMutex) {
        if (username_.empty()) {
            connected = mqtt_.connect(robotId_.c_str());
        } else {
            connected = mqtt_.connect(robotId_.c_str(), username_.c_str(), password_.c_str());
        }

        const uint32_t elapsedMs = mara::getSystemClock().millis() - startMs;

        if (connected) {
            Serial.printf("[MQTT] Connected in %lu ms\n", static_cast<unsigned long>(elapsedMs));

            bool ok1 = mqtt_.subscribe(topicCmd_.c_str());
            bool ok2 = mqtt_.subscribe(topicDiscovery_.c_str());

            Serial.printf("[MQTT] Sub cmd=%d (%s)\n", ok1, topicCmd_.c_str());
            Serial.printf("[MQTT] Sub discover=%d (%s)\n", ok2, topicDiscovery_.c_str());

            consecutiveFailures_ = 0;
            nextReconnectAttemptMs_ = mara::getSystemClock().millis() + RECONNECT_INTERVAL_MS;
        } else {
            consecutiveFailures_++;
            if (retriesExhausted()) {
                nextReconnectAttemptMs_ = UINT32_MAX;
                Serial.printf("[MQTT] Failed after %lu ms, rc=%d, giving up after %u attempts\n",
                    static_cast<unsigned long>(elapsedMs),
                    mqtt_.state(),
                    static_cast<unsigned>(MAX_RETRIES));
            } else {
                nextReconnectAttemptMs_ = mara::getSystemClock().millis() + nextReconnectDelayMs();
                Serial.printf("[MQTT] Failed after %lu ms, rc=%d, next retry in %lu ms\n",
                    static_cast<unsigned long>(elapsedMs),
                    mqtt_.state(),
                    static_cast<unsigned long>(nextReconnectAttemptMs_ - mara::getSystemClock().millis()));
            }
        }

        xSemaphoreGive(mqttMutex_);
    } else {
        Serial.println("[MQTT] Failed to acquire mutex for connect");
        consecutiveFailures_++;
        nextReconnectAttemptMs_ = mara::getSystemClock().millis() + nextReconnectDelayMs();
    }

    // Publish discovery response after releasing mutex (it will re-acquire)
    if (connected) {
        publishDiscoveryResponse();
    }

    connectInProgress_ = false;
    connectTask_ = nullptr;
    halConnectTask_.native = nullptr;

    // Delete self - use HAL if available
    if (halScheduler_) {
        halScheduler_->deleteCurrentTask();
    }
#if HAS_FREERTOS
    else {
        vTaskDelete(nullptr);
    }
#endif
}

uint32_t MqttTransport::nextReconnectDelayMs() const {
    uint32_t delayMs = RECONNECT_INTERVAL_MS;
    for (uint8_t i = 1; i < consecutiveFailures_; ++i) {
        if (delayMs >= (MAX_RECONNECT_INTERVAL_MS / 2)) {
            return MAX_RECONNECT_INTERVAL_MS;
        }
        delayMs *= 2;
    }
    return delayMs > MAX_RECONNECT_INTERVAL_MS ? MAX_RECONNECT_INTERVAL_MS : delayMs;
}

bool MqttTransport::retriesExhausted() const {
    return consecutiveFailures_ >= MAX_RETRIES;
}

void MqttTransport::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    std::string t(topic);

    if (t == topicCmd_) {
        // Copy payload to buffer for frame extraction
        std::vector<uint8_t> rxBuffer(payload, payload + length);

        // Extract frames using Protocol (same as UART/WiFi/BLE transports)
        // This parses [0xAA][len][len][msg_type][payload][crc] and delivers [msg_type][payload]
        Protocol::extractFrames(rxBuffer, [this](const uint8_t* frame, size_t len) {
            // Preferred: callback with explicit reply fn (V2 API)
            if (frameCallbackV2_) {
                auto reply = [this](const uint8_t* data, size_t len) -> bool {
                    return this->sendBytes(data, len);  // publishes to mara/{node}/ack
                };
                frameCallbackV2_(frame, len, reply);
                return;
            }

            // Legacy: MqttTransport-specific callback
            if (frameCallback_) {
                frameCallback_(frame, len);
                return;
            }

            // Base class handler (set by MultiTransport::begin())
            if (handler_) {
                handler_(frame, len);
                return;
            }

            Serial.println("[MQTT] RX cmd but no frame handler set");
        });
        return;
    }

    if (t == topicDiscovery_) {
        publishDiscoveryResponse();
        return;
    }
}

bool MqttTransport::sendBytes(const uint8_t* data, size_t len) {
    bool result = false;
    if (mqttMutex_ && xSemaphoreTake(mqttMutex_, pdMS_TO_TICKS(100)) == pdTRUE) {
        if (mqtt_.connected()) {
            result = mqtt_.publish(topicAck_.c_str(), data, len);
        }
        xSemaphoreGive(mqttMutex_);
    }
    return result;
}

void MqttTransport::publishDiscoveryResponse() {
    JsonDocument doc;

    // Keep robot_id, but ALSO provide node_id for host compatibility
    doc["robot_id"] = robotId_.c_str();
    doc["node_id"]  = robotId_.c_str();

    #ifdef MARA_FIRMWARE_VERSION
        doc["firmware"] = MARA_FIRMWARE_VERSION;
    #else
        doc["firmware"] = "1.0.0";
    #endif

    #ifdef MARA_PROTOCOL_VERSION
        doc["protocol"] = MARA_PROTOCOL_VERSION;
    #else
        doc["protocol"] = 1;
    #endif

    #ifdef MARA_BOARD_TYPE
        doc["board"] = MARA_BOARD_TYPE;
    #else
        doc["board"] = "esp32";
    #endif

    // Lowercase matches your Python NodeState Enum values
    doc["state"] = "online";

    // Use larger buffer to prevent silent truncation
    char out[512];
    size_t n = serializeJson(doc, out, sizeof(out));

    // Check for truncation (serializeJson returns bytes that would have been written)
    if (n >= sizeof(out)) {
        Serial.printf("[MQTT] WARNING: Discovery JSON truncated (%zu >= %zu)\n", n, sizeof(out));
        n = sizeof(out) - 1;  // Ensure null termination
    }

    // Thread-safe publish
    if (mqttMutex_ && xSemaphoreTake(mqttMutex_, pdMS_TO_TICKS(100)) == pdTRUE) {
        mqtt_.publish("mara/fleet/discover_response", out, n);
        xSemaphoreGive(mqttMutex_);
    }
}

#endif // HAS_MQTT_TRANSPORT && HAS_WIFI
