// src/core/MqttTransport.cpp

#include "config/FeatureFlags.h"

#if HAS_MQTT_TRANSPORT && HAS_WIFI

#include "transport/MqttTransport.h"
#include "config/Version.h"
#include "core/Protocol.h"
#include <ArduinoJson.h>

static void dumpHexPrefix(const uint8_t* data, unsigned len, unsigned maxBytes = 16) {
    Serial.print("[MQTT] RX bytes: ");
    for (unsigned i = 0; i < len && i < maxBytes; i++) {
        Serial.printf("%02X ", data[i]);
    }
    if (len > maxBytes) Serial.print("...");
    Serial.println();
}

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

    mqtt_.setCallback([this](char* topic, uint8_t* payload, unsigned int length) {
        this->onMessage(topic, payload, length);
    });

    reconnect();
}

void MqttTransport::loop() {
    if (!mqtt_.connected()) {
        uint32_t now = millis();
        if (now - lastReconnectAttempt_ > RECONNECT_INTERVAL_MS) {
            lastReconnectAttempt_ = now;
            reconnect();
        }
    } else {
        mqtt_.loop();
    }
}

void MqttTransport::reconnect() {
    if (mqtt_.connected()) return;

    Serial.printf("[MQTT] Connecting to %s:%d as %s...\n",
        broker_.c_str(), port_, robotId_.c_str());

    bool connected = false;
    if (username_.empty()) {
        connected = mqtt_.connect(robotId_.c_str());
    } else {
        connected = mqtt_.connect(robotId_.c_str(), username_.c_str(), password_.c_str());
    }

    if (connected) {
        Serial.println("[MQTT] Connected!");

        bool ok1 = mqtt_.subscribe(topicCmd_.c_str());
        bool ok2 = mqtt_.subscribe(topicDiscovery_.c_str());

        Serial.printf("[MQTT] Sub cmd=%d (%s)\n", ok1, topicCmd_.c_str());
        Serial.printf("[MQTT] Sub discover=%d (%s)\n", ok2, topicDiscovery_.c_str());

        publishDiscoveryResponse();
    } else {
        Serial.printf("[MQTT] Failed, rc=%d\n", mqtt_.state());
    }
}

void MqttTransport::onMessage(char* topic, uint8_t* payload, unsigned int length) {
    std::string t(topic);

    if (t == topicCmd_) {
        // Optional debug
        // dumpHexPrefix(payload, length);

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
