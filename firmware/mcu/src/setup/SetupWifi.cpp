#include "config/FeatureFlags.h"

#if HAS_WIFI

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/Clock.h"

// TODO: Migrate to hal::IWifiManager for full platform portability
// Currently uses ESP32 WiFi APIs directly
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

// WiFi reconnection state
volatile bool g_wifiConnected = false;
volatile bool g_wifiReconnecting = false;
uint32_t g_lastReconnectAttempt = 0;
const uint32_t RECONNECT_INTERVAL_MS = 5000;

// WiFi event handler
void onWiFiEvent(WiFiEvent_t event) {
    switch (event) {
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.print("[WiFi][EVENT] Connected, IP: ");
            Serial.println(WiFi.localIP());
            g_wifiConnected = true;
            g_wifiReconnecting = false;
            break;

        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            Serial.println("[WiFi][EVENT] Disconnected from AP");
            g_wifiConnected = false;
            break;

        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("[WiFi][EVENT] Associated with AP");
            break;

        case ARDUINO_EVENT_WIFI_STA_LOST_IP:
            Serial.println("[WiFi][EVENT] Lost IP address");
            g_wifiConnected = false;
            break;

        default:
            break;
    }
}

class SetupWifiModule : public mara::ISetupModule {
public:
    const char* name() const override { return "WiFi"; }

    mara::Result<void> setup(mara::ServiceContext& ctx) override {
        Serial.println("[WiFi] Starting AP + STA with auto-reconnect...");

        // Register event handler BEFORE starting WiFi
        WiFi.onEvent(onWiFiEvent);

        WiFi.mode(WIFI_AP_STA);
        WiFi.persistent(false);

        // Enable auto-reconnect for stable connection
        WiFi.setAutoReconnect(true);
        WiFi.setAutoConnect(true);

        // Set WiFi power and sleep settings for stability
        WiFi.setTxPower(WIFI_POWER_19_5dBm);  // Max power
        WiFi.setSleep(false);  // Disable WiFi sleep for reliability

        Serial.print("[WiFi][STA] Connecting to ");
        Serial.println(WIFI_STA_SSID);

        WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);

        uint32_t start = mara::getSystemClock().millis();
        const uint32_t timeoutMs = 15000;  // Increased timeout

        while (WiFi.status() != WL_CONNECTED && mara::getSystemClock().millis() - start < timeoutMs) {
            delay(500);
            Serial.print(".");
        }
        Serial.println();

        if (WiFi.status() == WL_CONNECTED) {
            Serial.print("[WiFi][STA] Connected, IP: ");
            Serial.println(WiFi.localIP());
            Serial.print("[WiFi][STA] RSSI: ");
            Serial.print(WiFi.RSSI());
            Serial.println(" dBm");
            g_wifiConnected = true;
        } else {
            Serial.println("[WiFi][STA] Initial connect failed, will retry in background");
            g_wifiConnected = false;
        }

        // Always start AP for fallback access
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

#else // !HAS_WIFI

// Stub for non-WiFi platforms
#include "setup/ISetupModule.h"

mara::ISetupModule* getSetupWifiModule() {
    return nullptr;
}

#endif // HAS_WIFI
