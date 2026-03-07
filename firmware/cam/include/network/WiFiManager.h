#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <DNSServer.h>
#include "storage/ConfigStore.h"
#include "config/WifiSecrets.h"

enum class WiFiMode {
    DISCONNECTED,
    CONNECTING,
    CONNECTED_STA,
    AP_MODE
};

class WiFiManager {
public:
    WiFiManager();

    // Initialize with config
    bool begin(const NetworkConfig& config);

    // Main loop - handles reconnection
    void loop();

    // Get current mode
    WiFiMode getMode() const { return mode_; }

    // Get IP address
    IPAddress getIP() const;

    // Get hostname
    const char* getHostname() const { return hostname_; }

    // Check if connected
    bool isConnected() const { return mode_ == WiFiMode::CONNECTED_STA; }

    // Check if in AP mode
    bool isAPMode() const { return mode_ == WiFiMode::AP_MODE; }

    // Manually switch to AP mode
    void startAP();

    // Attempt to connect to STA
    void connectSTA(const char* ssid, const char* password);

    // Get RSSI
    int getRSSI() const;

    // Get MAC address
    String getMacAddress() const;

    // DNS server for captive portal (public for handler access)
    DNSServer* getDNSServer() { return &dnsServer_; }

private:
    WiFiMode mode_ = WiFiMode::DISCONNECTED;
    char hostname_[33] = DEFAULT_HOSTNAME;
    char ssid_[33] = "";
    char password_[65] = "";
    char apSsid_[33] = DEFAULT_AP_SSID;
    char apPassword_[65] = DEFAULT_AP_PASSWORD;
    uint8_t apChannel_ = DEFAULT_AP_CHANNEL;

    DNSServer dnsServer_;
    uint32_t lastReconnectAttempt_ = 0;
    uint32_t connectStartTime_ = 0;
    bool dnsStarted_ = false;

    void setupMDNS();
    void startDNS();
    void stopDNS();
};
