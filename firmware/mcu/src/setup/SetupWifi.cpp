#include "config/FeatureFlags.h"

#if HAS_WIFI

#include "setup/ISetupModule.h"
#include "core/ServiceContext.h"
#include "core/Clock.h"
#include "core/Debug.h"
#include "hal/ILogger.h"
#include "hal/IWifiManager.h"

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

// Helper to format IP address as string
void formatIp(const hal::IpAddress& ip, char* buf, size_t bufSize) {
    snprintf(buf, bufSize, "%d.%d.%d.%d", ip.octets[0], ip.octets[1], ip.octets[2], ip.octets[3]);
}

// WiFi event handler (static, uses DBG_* macros for HAL-based logging)
void onHalWifiEvent(hal::WifiEvent event) {
    switch (event) {
        case hal::WifiEvent::STA_GOT_IP:
            DBG_PRINTLN("[WiFi][EVENT] Connected, got IP");
            g_wifiConnected = true;
            g_wifiReconnecting = false;
            break;

        case hal::WifiEvent::STA_DISCONNECTED:
            DBG_PRINTLN("[WiFi][EVENT] Disconnected from AP");
            g_wifiConnected = false;
            break;

        case hal::WifiEvent::STA_CONNECTED:
            DBG_PRINTLN("[WiFi][EVENT] Associated with AP");
            break;

        case hal::WifiEvent::STA_LOST_IP:
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
        hal::IWifiManager* wifi = ctx.halWifi;

        if (!wifi) {
            if (logger) logger->println("[WiFi] HAL WiFi manager not available");
            return mara::Result<void>::err(mara::ErrorCode::NotSupported);
        }

        if (logger) logger->println("[WiFi] Starting AP + STA with auto-reconnect...");

        // Register event handler BEFORE starting WiFi
        wifi->onEvent(onHalWifiEvent);

        wifi->setMode(hal::WifiMode::AP_STA);
        wifi->setPersistent(false);

        // Enable auto-reconnect for stable connection
        wifi->setAutoReconnect(true);
        wifi->setAutoConnect(true);

        // Set WiFi power (max power = ~20 dBm)
        wifi->setTxPower(20);

        // Enable WiFi modem sleep for BT+WiFi coexistence
        // Note: Required when both WiFi and Bluetooth Classic are enabled
#if HAS_BLE
        wifi->setSleepEnabled(true);
        if (logger) logger->println("[WiFi] Modem sleep enabled for BT coexistence");
#else
        wifi->setSleepEnabled(false);
#endif

        if (logger) logger->printf("[WiFi][STA] Connecting to %s\n", WIFI_STA_SSID);

        wifi->beginSta(WIFI_STA_SSID, WIFI_STA_PASSWORD);

        // BLOCKING WAIT: This blocks setup for up to 15 seconds.
        // The ESP32 hardware watchdog (if enabled) has a default timeout of ~8 seconds.
        // We use mara::getSystemClock().delay(500) which yields to the scheduler.
        // If using a custom watchdog with shorter timeout, either:
        // 1. Disable watchdog during setup (not recommended), or
        // 2. Reduce this timeout, or
        // 3. Use non-blocking WiFi init with event callbacks (onHalWifiEvent handles this)
        //
        // Since wifi->setAutoReconnect(true) is set, if initial connect fails,
        // background reconnection will continue after setup completes.
        uint32_t start = mara::getSystemClock().millis();
        const uint32_t timeoutMs = 15000;

        while (!wifi->isStaConnected() && mara::getSystemClock().millis() - start < timeoutMs) {
            mara::getSystemClock().delay(500);  // Yields to FreeRTOS scheduler
            if (logger) logger->print(".");
        }
        if (logger) logger->println("");

        if (wifi->isStaConnected()) {
            char ipBuf[16];
            formatIp(wifi->getStaIp(), ipBuf, sizeof(ipBuf));
            if (logger) {
                logger->printf("[WiFi][STA] Connected, IP: %s\n", ipBuf);
                logger->printf("[WiFi][STA] RSSI: %d dBm\n", wifi->getStaRssi());
            }
            g_wifiConnected = true;
        } else {
            if (logger) logger->println("[WiFi][STA] Initial connect failed, will retry in background");
            g_wifiConnected = false;
        }

        // Always start AP for fallback access
        bool apOk = wifi->beginAp(AP_SSID, AP_PASS);
        if (apOk) {
            char apIpBuf[16];
            formatIp(wifi->getApIp(), apIpBuf, sizeof(apIpBuf));
            if (logger) logger->printf("[WiFi][AP] Started, SSID: %s  IP: %s\n", AP_SSID, apIpBuf);
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
