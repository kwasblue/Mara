// include/core/MqttTransport.h
#pragma once

#include "config/FeatureFlags.h"

#if HAS_MQTT_TRANSPORT && HAS_WIFI

#include <WiFi.h>
#include <PubSubClient.h>
#include "core/ITransport.h"
#include <string>
#include <functional>

class MqttTransport : public ITransport {
public:
    // Old handler (backward compatible)
    using FrameCallback = std::function<void(const uint8_t*, size_t)>;

    // New handler: includes a reply function that publishes to mara/{node}/ack
    using ReplyFn = std::function<bool(const uint8_t*, size_t)>;
    using FrameCallbackV2 = std::function<void(const uint8_t*, size_t, ReplyFn)>;

    MqttTransport(
        const char* broker,
        uint16_t port,
        const char* robotId,
        const char* username = nullptr,
        const char* password = nullptr
    );

    void begin() override;
    void loop() override;

    // Match ITransport return type
    bool sendBytes(const uint8_t* data, size_t len) override;

    // Existing API
    void setFrameHandler(FrameCallback cb) { frameCallback_ = cb; }

    // New API (preferred)
    void setFrameHandlerV2(FrameCallbackV2 cb) { frameCallbackV2_ = cb; }

    // PubSubClient::connected() not const
    bool isConnected() { return mqtt_.connected(); }

private:
    void reconnect();
    void onMessage(char* topic, uint8_t* payload, unsigned int length);
    void publishDiscoveryResponse();

    WiFiClient wifi_;
    PubSubClient mqtt_;

    std::string broker_;
    uint16_t port_;
    std::string robotId_;
    std::string username_;
    std::string password_;

    // Topics
    std::string topicCmd_;
    std::string topicAck_;
    std::string topicTelemetry_;
    std::string topicState_;
    std::string topicDiscovery_;

    FrameCallback frameCallback_;       // legacy
    FrameCallbackV2 frameCallbackV2_;   // preferred

    uint32_t lastReconnectAttempt_ = 0;
    static constexpr uint32_t RECONNECT_INTERVAL_MS = 5000;
};

#else // !HAS_MQTT_TRANSPORT || !HAS_WIFI

#include "core/ITransport.h"

class MqttTransport : public ITransport {
public:
    using FrameCallback = std::function<void(const uint8_t*, size_t)>;
    using ReplyFn = std::function<bool(const uint8_t*, size_t)>;
    using FrameCallbackV2 = std::function<void(const uint8_t*, size_t, ReplyFn)>;

    MqttTransport(const char*, uint16_t, const char*, const char* = nullptr, const char* = nullptr) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
    void setFrameHandler(FrameCallback) {}
    void setFrameHandlerV2(FrameCallbackV2) {}
    bool isConnected() { return false; }
};

#endif // HAS_MQTT_TRANSPORT && HAS_WIFI
