#include "command/MessageRouter.h"
#include "core/Debug.h"
#include "command/BinaryCommands.h"
#include "config/Version.h"
#include "config/DeviceManifest.h"
#include "core/Clock.h"
#include <ArduinoJson.h>

std::atomic<MessageRouter*> MessageRouter::s_instance{nullptr};

MessageRouter::MessageRouter(EventBus& bus, ITransport& transport)
    : bus_(bus)
    , transport_(transport)
{
    // Release ensures all constructor writes are visible before pointer is published
    s_instance.store(this, std::memory_order_release);
}

void MessageRouter::setup() {
    transport_.setFrameHandler(
        [this](const uint8_t* frame, size_t len) { this->onFrame(frame, len); }
    );
    transport_.begin();

    bus_.subscribe(&MessageRouter::onEventStatic);

    txBuffer_.reserve(64);
}

void MessageRouter::loop() {
    transport_.loop();
}

void MessageRouter::onEventStatic(const Event& evt) {
    // Acquire ensures we see all constructor writes before using the instance
    MessageRouter* instance = s_instance.load(std::memory_order_acquire);
    if (instance) {
        instance->onEvent(evt);
    }
}

void MessageRouter::onFrame(const uint8_t* frame, size_t len) {
    if (len == 0) return;
    uint8_t msgType = frame[0];
    uint32_t now_ms = mara::getSystemClock().millis();

    switch (msgType) {
    case Protocol::MSG_PING: {
        Event evt{ EventType::PING, now_ms, EventPayload{} };
        bus_.publish(evt);
        sendSimple(Protocol::MSG_PONG);
        break;
    }
    
    case Protocol::MSG_PONG: {
        Event evt{ EventType::PONG, now_ms, EventPayload{} };
        bus_.publish(evt);
        break;
    }

    case Protocol::MSG_HEARTBEAT: {
        // Host sent a heartbeat - publish as BIN_MESSAGE_RX so CommandRegistry
        // calls onHostHeartbeat() to reset the host timeout
        Event evt;
        evt.type = EventType::BIN_MESSAGE_RX;
        evt.timestamp_ms = now_ms;
        evt.payload.bin = { static_cast<uint8_t>(BinaryCommands::Opcode::HEARTBEAT) };
        bus_.publish(evt);
        break;
    }

    case Protocol::MSG_VERSION_REQUEST: {
        DBG_PRINTLN("[Router] VERSION_REQUEST received");
        sendVersionResponse();
        break;
    }

    case Protocol::MSG_WHOAMI: {
        Event evt;
        evt.type         = EventType::WHOMAI_REQUEST;
        evt.timestamp_ms = now_ms;
        evt.payload      = {};
        bus_.publish(evt);
        break;
    }

    case Protocol::MSG_CMD_JSON: {
        if (len <= 1) {
            return;
        }
        const uint8_t* jsonData = frame + 1;
        size_t jsonLen          = len - 1;

        std::string jsonStr(reinterpret_cast<const char*>(jsonData), jsonLen);

        Event evt;
        evt.type         = EventType::JSON_MESSAGE_RX;
        evt.timestamp_ms = now_ms;
        evt.payload      = {};
        evt.payload.json = std::move(jsonStr);

        bus_.publish(evt);
        break;
    }

    case Protocol::MSG_CMD_BIN: {
        if (len <= 1) {
            DBG_PRINTLN("[Router] MSG_CMD_BIN with no payload");
            return;
        }
        // Binary command format: [opcode][payload...]
        // Pass the binary data as a BIN_MESSAGE_RX event
        const uint8_t* binData = frame + 1;
        size_t binLen = len - 1;

        Event evt;
        evt.type = EventType::BIN_MESSAGE_RX;
        evt.timestamp_ms = now_ms;
        evt.payload.bin.assign(binData, binData + binLen);

        bus_.publish(evt);
        break;
    }

    default:
        DBG_PRINTF("[Router] Unknown msgType: 0x%02X\n", msgType);
        break;
    }
}

void MessageRouter::onEvent(const Event& evt) {
    switch (evt.type) {
    case EventType::HEARTBEAT:
        sendSimple(Protocol::MSG_HEARTBEAT);
        break;

    case EventType::JSON_MESSAGE_TX: {
        const std::string& json = evt.payload.json;
        if (json.empty()) {
            DBG_PRINTLN("[Router] JSON_MESSAGE_TX with empty payload");
            return;
        }

        DBG_PRINTF("[Router] TX JSON (%u bytes): %s\n",
                   (unsigned)json.size(), json.c_str());

        txBuffer_.clear();
        Protocol::encode(
            Protocol::MSG_CMD_JSON,
            reinterpret_cast<const uint8_t*>(json.data()),
            json.size(),
            txBuffer_
        );

        if (!txBuffer_.empty()) {
            transport_.sendBytes(txBuffer_.data(), txBuffer_.size());
        } else {
            DBG_PRINTLN("[Router] encode() produced empty buffer");
        }
        break;
    }
    case EventType::BIN_MESSAGE_TX: {
        const std::vector<uint8_t>& bin = evt.payload.bin;
        if (bin.empty()) {
            DBG_PRINTLN("[Router] BIN_MESSAGE_TX with empty payload");
            return;
        }

        DBG_PRINTF("[Router] TX BIN (%u bytes)\n", (unsigned)bin.size());

        txBuffer_.clear();
        Protocol::encode(
            Protocol::MSG_TELEMETRY_BIN,
            bin.data(),
            bin.size(),
            txBuffer_
        );

        if (!txBuffer_.empty()) {
            transport_.sendBytes(txBuffer_.data(), txBuffer_.size());
        } else {
            DBG_PRINTLN("[Router] encode() produced empty buffer");
        }
        break;
    }
    default:
        break;
    }
}

void MessageRouter::sendSimple(uint8_t msgType) {
    txBuffer_.clear();                 // ✅ add this
    Protocol::encode(msgType, nullptr, 0, txBuffer_);
    if (!txBuffer_.empty()) {
        transport_.sendBytes(txBuffer_.data(), txBuffer_.size());
    }
}

void MessageRouter::sendVersionResponse() {
    using namespace mara;

    // Build capability mask from compile-time flags
    uint32_t caps = buildDeviceCaps();

    JsonDocument doc;
    doc["firmware"]       = Version::FIRMWARE;
    doc["protocol"]       = Version::PROTOCOL;
    doc["schema_version"] = Version::SCHEMA_VERSION;
    doc["board"]          = Version::BOARD;
    doc["name"]           = Version::NAME;
    doc["capabilities"]   = caps;

    // Feature array - must match IdentityModule::publishIdentity()
    JsonArray features = doc["features"].to<JsonArray>();
    if (caps & DeviceCap::UART) features.add("uart");
    if (caps & DeviceCap::WIFI) features.add("wifi");
    if (caps & DeviceCap::BLE) features.add("ble");
    if (caps & DeviceCap::MQTT) features.add("mqtt");
    if (caps & DeviceCap::DC_MOTOR) features.add("dc_motor");
    if (caps & DeviceCap::SERVO) features.add("servo");
    if (caps & DeviceCap::STEPPER) features.add("stepper");
    if (caps & DeviceCap::MOTION_CTRL) features.add("motion_ctrl");
    if (caps & DeviceCap::ENCODER) features.add("encoder");
    if (caps & DeviceCap::IMU) features.add("imu");
    if (caps & DeviceCap::LIDAR) features.add("lidar");
    if (caps & DeviceCap::ULTRASONIC) features.add("ultrasonic");
    if (caps & DeviceCap::SIGNAL_BUS) features.add("signal_bus");
    if (caps & DeviceCap::CONTROL_KERNEL) features.add("control_kernel");
    if (caps & DeviceCap::OBSERVER) features.add("observer");
    if (caps & DeviceCap::TELEMETRY) features.add("telemetry");
    if (caps & DeviceCap::GPIO) features.add("gpio");
    if (caps & DeviceCap::PWM) features.add("pwm");

    std::string json;
    serializeJson(doc, json);

    DBG_PRINTF("[Router] VERSION_RESPONSE: %s\n", json.c_str());

    txBuffer_.clear();
    Protocol::encode(
        Protocol::MSG_VERSION_RESPONSE,
        reinterpret_cast<const uint8_t*>(json.data()),
        json.size(),
        txBuffer_
    );

    if (!txBuffer_.empty()) {
        transport_.sendBytes(txBuffer_.data(), txBuffer_.size());
    }
}