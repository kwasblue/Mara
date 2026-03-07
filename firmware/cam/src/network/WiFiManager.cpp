#include "network/WiFiManager.h"
#include "utils/Logger.h"

static const char* TAG = "WiFi";

WiFiManager::WiFiManager() {}

bool WiFiManager::begin(const NetworkConfig& config) {
    LOG_INFO(TAG, "Initializing WiFi manager");

    // Store config
    strncpy(hostname_, config.hostname, sizeof(hostname_) - 1);
    strncpy(apSsid_, config.apSsid, sizeof(apSsid_) - 1);
    strncpy(apPassword_, config.apPassword, sizeof(apPassword_) - 1);
    apChannel_ = config.apChannel;

    // Determine SSID/password source
    if (config.configured && strlen(config.ssid) > 0) {
        strncpy(ssid_, config.ssid, sizeof(ssid_) - 1);
        strncpy(password_, config.password, sizeof(password_) - 1);
        LOG_INFO(TAG, "Using stored WiFi credentials");
    } else {
        // Fall back to compile-time credentials
        strncpy(ssid_, CAM_WIFI_SSID, sizeof(ssid_) - 1);
        strncpy(password_, CAM_WIFI_PASSWORD, sizeof(password_) - 1);
        LOG_INFO(TAG, "Using compiled WiFi credentials");
    }

    WiFi.setHostname(hostname_);
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);

    // Start connection
    if (strlen(ssid_) > 0) {
        connectSTA(ssid_, password_);
    } else {
        LOG_WARN(TAG, "No WiFi credentials, starting AP mode");
        startAP();
    }

    return true;
}

void WiFiManager::loop() {
    // Process DNS if in AP mode
    if (dnsStarted_) {
        dnsServer_.processNextRequest();
    }

    // Handle state transitions
    switch (mode_) {
        case WiFiMode::CONNECTING: {
            if (WiFi.status() == WL_CONNECTED) {
                mode_ = WiFiMode::CONNECTED_STA;
                LOG_INFO(TAG, "Connected! IP: %s", WiFi.localIP().toString().c_str());
                setupMDNS();
            } else if (millis() - connectStartTime_ > DEFAULT_WIFI_TIMEOUT_MS) {
                LOG_WARN(TAG, "Connection timeout, switching to AP mode");
                startAP();
            }
            break;
        }

        case WiFiMode::CONNECTED_STA: {
            if (WiFi.status() != WL_CONNECTED) {
                mode_ = WiFiMode::DISCONNECTED;
                LOG_WARN(TAG, "WiFi disconnected");
            }
            break;
        }

        case WiFiMode::DISCONNECTED: {
            uint32_t now = millis();
            if (now - lastReconnectAttempt_ > DEFAULT_RECONNECT_INTERVAL_MS) {
                lastReconnectAttempt_ = now;
                if (strlen(ssid_) > 0) {
                    LOG_INFO(TAG, "Attempting reconnection...");
                    connectSTA(ssid_, password_);
                }
            }
            break;
        }

        case WiFiMode::AP_MODE:
            // AP mode is stable, nothing to do
            break;
    }
}

void WiFiManager::connectSTA(const char* ssid, const char* password) {
    LOG_INFO(TAG, "Connecting to %s...", ssid);

    stopDNS();
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    mode_ = WiFiMode::CONNECTING;
    connectStartTime_ = millis();
}

void WiFiManager::startAP() {
    LOG_INFO(TAG, "Starting AP: %s", apSsid_);

    WiFi.mode(WIFI_AP);
    WiFi.softAP(apSsid_, apPassword_, apChannel_);

    mode_ = WiFiMode::AP_MODE;
    LOG_INFO(TAG, "AP started, IP: %s", WiFi.softAPIP().toString().c_str());

    setupMDNS();
    startDNS();
}

void WiFiManager::setupMDNS() {
    if (MDNS.begin(hostname_)) {
        MDNS.addService("http", "tcp", 80);
        LOG_INFO(TAG, "mDNS started: %s.local", hostname_);
    } else {
        LOG_ERROR(TAG, "mDNS failed to start");
    }
}

void WiFiManager::startDNS() {
    if (!dnsStarted_) {
        // Redirect all DNS queries to our IP (captive portal)
        dnsServer_.start(53, "*", WiFi.softAPIP());
        dnsStarted_ = true;
        LOG_INFO(TAG, "DNS server started for captive portal");
    }
}

void WiFiManager::stopDNS() {
    if (dnsStarted_) {
        dnsServer_.stop();
        dnsStarted_ = false;
    }
}

IPAddress WiFiManager::getIP() const {
    if (mode_ == WiFiMode::AP_MODE) {
        return WiFi.softAPIP();
    }
    return WiFi.localIP();
}

int WiFiManager::getRSSI() const {
    if (mode_ == WiFiMode::CONNECTED_STA) {
        return WiFi.RSSI();
    }
    return 0;
}

String WiFiManager::getMacAddress() const {
    return WiFi.macAddress();
}
