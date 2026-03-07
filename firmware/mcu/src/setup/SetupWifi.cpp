#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"

#include <Arduino.h>
#include <WiFi.h>

#include "config/WifiSecrets.h"
#include "transport/WifiTransport.h"

// WiFi defaults if WifiSecrets.h not configured
#ifndef WIFI_STA_SSID
#define WIFI_STA_SSID "YourHomeSSID"
#endif

#ifndef WIFI_STA_PASSWORD
#define WIFI_STA_PASSWORD "YourHomePassword"
#endif

namespace {

// AP = robot's own network
const char* AP_SSID = "RobotAP";
const char* AP_PASS = "robotpass";

class SetupWifiModule : public mara::ISetupModule {
public:
    const char* name() const override { return "WiFi"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        Serial.println("[WiFi] Starting AP + optional STA...");

        WiFi.mode(WIFI_AP_STA);
        WiFi.persistent(false);
        WiFi.setAutoReconnect(false);
        WiFi.setAutoConnect(false);

        Serial.print("[WiFi][STA] Connecting to ");
        Serial.print(WIFI_STA_SSID);

        WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);

        uint32_t start = millis();
        const uint32_t timeoutMs = 10000;

        while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
            delay(500);
            Serial.print(".");
        }
        Serial.println();

        if (WiFi.status() == WL_CONNECTED) {
            Serial.print("[WiFi][STA] Connected, IP: ");
            Serial.println(WiFi.localIP());
        } else {
            Serial.println("[WiFi][STA] Failed; disabling STA to avoid reconnect spam.");
            WiFi.disconnect(true, true);
            WiFi.mode(WIFI_AP);
        }

        bool apOk = WiFi.softAP(AP_SSID, AP_PASS);
        if (apOk) {
            IPAddress apIp = WiFi.softAPIP();
            Serial.print("[WiFi][AP] Started, SSID: ");
            Serial.print(AP_SSID);
            Serial.print("  IP: ");
            Serial.println(apIp);
        } else {
            Serial.println("[WiFi][AP] Failed to start AP!");
        }

        // Initialize WiFi transport if available
        if (ctx.wifi) {
            ctx.wifi->begin();
        }

        return mara::Result<void>::ok();
    }
};

SetupWifiModule g_setupWifi;

} // anonymous namespace

// Global accessor for setup module array
mara::ISetupModule* getSetupWifiModule() {
    return &g_setupWifi;
}
