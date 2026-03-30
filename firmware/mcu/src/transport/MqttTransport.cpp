// src/core/MqttTransport.cpp

#include "config/FeatureFlags.h"

#if HAS_MQTT_TRANSPORT && HAS_WIFI

#include "transport/MqttTransport.h"
#include "config/Version.h"
#include "core/Protocol.h"
#include <ArduinoJson.h>

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
}

void MqttTransport::begin() {
    mqtt_.setServer(broker_.c_str(), port_);
    mqtt_.setBufferSize(1024);
    mqtt_.setKeepAlive(5);
    mqtt_.setSocketTimeout(1);

    mqtt_.setCallback([this](char* topic, uint8_t* payload, unsigned int length) {
        this->onMessage(topic, payload, length);
    });

    nextReconnectAttemptMs_ = millis();
}

void MqttTransport::loop() {
    if (mqtt_.connected()) {
        consecutiveFailures_ = 0;
        mqtt_.loop();
        return;
    }

    if (connectInProgress_) {
        return;
    }

    if (WiFi.status() != WL_CONNECTED) {
        return;
    }

    if (retriesExhausted()) {
        return;
    }

    uint32_t now = millis();
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
                nextReconnectAttemptMs_ = millis() + nextReconnectDelayMs();
                Serial.println("[MQTT] Failed to start connect task (HAL); backing off");
            }
        }
        return;
    }

    // Direct FreeRTOS path (legacy)
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
            nextReconnectAttemptMs_ = millis() + nextReconnectDelayMs();
            Serial.println("[MQTT] Failed to start connect task; backing off");
        }
    }
}

void MqttTransport::connectTaskEntry(void* arg) {
    auto* self = static_cast<MqttTransport*>(arg);
    self->connectTaskBody();
}

void MqttTransport::connectTaskBody() {
    Serial.printf("[MQTT] Connecting to %s:%d as %s...\n",
        broker_.c_str(), port_, robotId_.c_str());

    const uint32_t startMs = millis();

    bool connected = false;
    if (username_.empty()) {
        connected = mqtt_.connect(robotId_.c_str());
    } else {
        connected = mqtt_.connect(robotId_.c_str(), username_.c_str(), password_.c_str());
    }

    const uint32_t elapsedMs = millis() - startMs;

    if (connected) {
        Serial.printf("[MQTT] Connected in %lu ms\n", static_cast<unsigned long>(elapsedMs));

        bool ok1 = mqtt_.subscribe(topicCmd_.c_str());
        bool ok2 = mqtt_.subscribe(topicDiscovery_.c_str());

        Serial.printf("[MQTT] Sub cmd=%d (%s)\n", ok1, topicCmd_.c_str());
        Serial.printf("[MQTT] Sub discover=%d (%s)\n", ok2, topicDiscovery_.c_str());

        consecutiveFailures_ = 0;
        nextReconnectAttemptMs_ = millis() + RECONNECT_INTERVAL_MS;
        publishDiscoveryResponse();
    } else {
        consecutiveFailures_++;
        if (retriesExhausted()) {
            nextReconnectAttemptMs_ = UINT32_MAX;
            Serial.printf("[MQTT] Failed after %lu ms, rc=%d, giving up after %u attempts\n",
                static_cast<unsigned long>(elapsedMs),
                mqtt_.state(),
                static_cast<unsigned>(MAX_RETRIES));
        } else {
            nextReconnectAttemptMs_ = millis() + nextReconnectDelayMs();
            Serial.printf("[MQTT] Failed after %lu ms, rc=%d, next retry in %lu ms\n",
                static_cast<unsigned long>(elapsedMs),
                mqtt_.state(),
                static_cast<unsigned long>(nextReconnectAttemptMs_ - millis()));
        }
    }

    connectInProgress_ = false;
    connectTask_ = nullptr;
    halConnectTask_.native = nullptr;

    // Delete self - use HAL if available
    if (halScheduler_) {
        halScheduler_->deleteCurrentTask();
    } else {
        vTaskDelete(nullptr);
    }
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
    if (!mqtt_.connected()) return false;
    return mqtt_.publish(topicAck_.c_str(), data, len);
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

    char out[256];
    size_t n = serializeJson(doc, out, sizeof(out));
    mqtt_.publish("mara/fleet/discover_response", out, n);
}

#endif // HAS_MQTT_TRANSPORT && HAS_WIFI
