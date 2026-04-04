#include "config/FeatureFlags.h"

#if HAS_WIFI

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/Clock.h"
#include "core/Debug.h"
#include "hal/ILogger.h"

// TODO: Migrate to hal::IWifiManager for full platform portability
// Currently uses ESP32 WiFi APIs directly (guarded by HAS_WIFI)
#include <WiFi.h>

#include "config/WifiSecrets.h"
#include "transport/WifiTransport.h"

// WiFi defaults if WifiSecrets.h not configured
// WARNING: These are placeholder credentials. For production:
// 1. Create WifiSecrets.h with real credentials, OR
// 2. Define these in platformio.ini build_flags
#ifndef WIFI_STA_SSID
#define WIFI_STA_SSID "YourHomeSSID"
#endif

#ifndef WIFI_STA_PASSWORD
#define WIFI_STA_PASSWORD "YourHomePassword"
#endif

// AP (Access Point) credentials - robot's own network for fallback access
// SECURITY: Override these in WifiSecrets.h or build_flags for production!
// Anyone knowing these defaults can connect to your robot's AP.
#ifndef WIFI_AP_SSID
#define WIFI_AP_SSID "RobotAP"
#endif

#ifndef WIFI_AP_PASSWORD
#define WIFI_AP_PASSWORD "robotpass"
#endif

namespace {

// AP = robot's own network (use config defines)
const char* AP_SSID = WIFI_AP_SSID;
const char* AP_PASS = WIFI_AP_PASSWORD;

// WiFi reconnection state
volatile bool g_wifiConnected = false;
volatile bool g_wifiReconnecting = false;
uint32_t g_lastReconnectAttempt = 0;
const uint32_t RECONNECT_INTERVAL_MS = 5000;

// WiFi event handler (static, uses DBG_* macros for HAL-based logging)
void onWiFiEvent(WiFiEvent_t event) {
    switch (event) {
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            DBG_PRINTF("[WiFi][EVENT] Connected, IP: %s\n", WiFi.localIP().toString().c_str());
            g_wifiConnected = true;
            g_wifiReconnecting = false;
            break;

        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            DBG_PRINTLN("[WiFi][EVENT] Disconnected from AP");
            g_wifiConnected = false;
            break;

        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            DBG_PRINTLN("[WiFi][EVENT] Associated with AP");
            break;

        case ARDUINO_EVENT_WIFI_STA_LOST_IP:
            DBG_PRINTLN("[WiFi][EVENT] Lost IP address");
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
        hal::ILogger* logger = ctx.halLogger;
        if (logger) logger->println("[WiFi] Starting AP + STA with auto-reconnect...");

        // Register event handler BEFORE starting WiFi
        WiFi.onEvent(onWiFiEvent);

        WiFi.mode(WIFI_AP_STA);
        WiFi.persistent(false);

        // Enable auto-reconnect for stable connection
        WiFi.setAutoReconnect(true);
        WiFi.setAutoConnect(true);

        // Set WiFi power and sleep settings
        WiFi.setTxPower(WIFI_POWER_19_5dBm);  // Max power

        // Enable WiFi modem sleep for BT+WiFi coexistence
        // Note: Required when both WiFi and Bluetooth Classic are enabled
#if HAS_BLE
        WiFi.setSleep(true);   // Enable modem sleep for BT coexistence
        if (logger) logger->println("[WiFi] Modem sleep enabled for BT coexistence");
#else
        WiFi.setSleep(false);  // Disable WiFi sleep for reliability (no BT)
#endif

        if (logger) logger->printf("[WiFi][STA] Connecting to %s\n", WIFI_STA_SSID);

        WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);

        // BLOCKING WAIT: This blocks setup for up to 15 seconds.
        // The ESP32 hardware watchdog (if enabled) has a default timeout of ~8 seconds.
        // We use mara::getSystemClock().delay(500) which yields to the scheduler.
        // If using a custom watchdog with shorter timeout, either:
        // 1. Disable watchdog during setup (not recommended), or
        // 2. Reduce this timeout, or
        // 3. Use non-blocking WiFi init with event callbacks (onWiFiEvent handles this)
        //
        // Since WiFi.setAutoReconnect(true) is set, if initial connect fails,
        // background reconnection will continue after setup completes.
        uint32_t start = mara::getSystemClock().millis();
        const uint32_t timeoutMs = 15000;

        while (WiFi.status() != WL_CONNECTED && mara::getSystemClock().millis() - start < timeoutMs) {
            mara::getSystemClock().delay(500);  // Yields to FreeRTOS scheduler
            if (logger) logger->print(".");
        }
        if (logger) logger->println("");

        if (WiFi.status() == WL_CONNECTED) {
            if (logger) {
                logger->printf("[WiFi][STA] Connected, IP: %s\n", WiFi.localIP().toString().c_str());
                logger->printf("[WiFi][STA] RSSI: %d dBm\n", WiFi.RSSI());
            }
            g_wifiConnected = true;
        } else {
            if (logger) logger->println("[WiFi][STA] Initial connect failed, will retry in background");
            g_wifiConnected = false;
        }

        // Always start AP for fallback access
        bool apOk = WiFi.softAP(AP_SSID, AP_PASS);
        if (apOk) {
            IPAddress apIp = WiFi.softAPIP();
            if (logger) logger->printf("[WiFi][AP] Started, SSID: %s  IP: %s\n", AP_SSID, apIp.toString().c_str());
        } else {
            if (logger) logger->println("[WiFi][AP] Failed to start AP!");
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
