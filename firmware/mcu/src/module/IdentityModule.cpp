#include "module/IdentityModule.h"
#include "core/Debug.h"
#include <Arduino.h>
#include <ArduinoJson.h>

#include "config/Version.h"         // auto-generated Version::*
#include "config/DeviceManifest.h"  // unified capabilities

IdentityModule* IdentityModule::s_instance = nullptr;

void IdentityModule::setup() {
    s_instance = this;
    bus_.subscribe(&IdentityModule::onEventStatic);
    DBG_PRINTLN("[IdentityModule] setup complete");
}

void IdentityModule::loop(uint32_t /*now_ms*/) {
    // Nothing periodic for now
}

void IdentityModule::onEventStatic(const Event& evt) {
    if (s_instance) {
        s_instance->handleEvent(evt);
    }
}

static void publishIdentity(EventBus& bus) {
    using namespace mara;

    // Build unified capability mask
    uint32_t caps = buildDeviceCaps();

    JsonDocument doc;
    doc["kind"]           = "identity";
    doc["protocol"]       = Version::PROTOCOL;
    doc["schema_version"] = Version::SCHEMA_VERSION;
    doc["firmware"]       = Version::FIRMWARE;
    doc["board"]          = Version::BOARD;
    doc["name"]           = Version::NAME;
    doc["capabilities"]   = caps;

    // Feature array - use direct string literals (matching IdentityHandler pattern)
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

    // Add loop rates
    const auto& rates = getLoopRates();
    JsonObject timing = doc["timing"].to<JsonObject>();
    timing["control_hz"] = rates.ctrl_hz;
    timing["telemetry_hz"] = rates.telem_hz;
    timing["safety_hz"] = rates.safety_hz;

    std::string out;
    serializeJson(doc, out);

    Event tx{};
    tx.type = EventType::JSON_MESSAGE_TX;
    tx.timestamp_ms = 0;
    tx.payload.json = out;
    bus.publish(tx);
}

void IdentityModule::handleEvent(const Event& evt) {
    if (evt.type == EventType::WHOMAI_REQUEST) {
        DBG_PRINTLN("[IDENTITY] WHOAMI request received");
        publishIdentity(bus_);
    }
}
