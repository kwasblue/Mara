// src/hal/esp32/Esp32WifiManager.cpp
// ESP32 WiFi manager implementation

#include "config/PlatformConfig.h"

#if PLATFORM_ESP32

#include "hal/esp32/Esp32WifiManager.h"
#include <WiFi.h>
#include <cstring>

namespace hal {

WifiEventCallback Esp32WifiManager::eventCallback_ = nullptr;

void Esp32WifiManager::setMode(WifiMode mode) {
    wifi_mode_t espMode;
    switch (mode) {
        case WifiMode::OFF:    espMode = WIFI_OFF; break;
        case WifiMode::STA:    espMode = WIFI_STA; break;
        case WifiMode::AP:     espMode = WIFI_AP; break;
        case WifiMode::AP_STA: espMode = WIFI_AP_STA; break;
        default:               espMode = WIFI_OFF; break;
    }
    WiFi.mode(espMode);
}

WifiMode Esp32WifiManager::getMode() const {
    wifi_mode_t espMode = WiFi.getMode();
    switch (espMode) {
        case WIFI_OFF:    return WifiMode::OFF;
        case WIFI_STA:    return WifiMode::STA;
        case WIFI_AP:     return WifiMode::AP;
        case WIFI_AP_STA: return WifiMode::AP_STA;
        default:          return WifiMode::OFF;
    }
}

void Esp32WifiManager::setPersistent(bool enabled) {
    WiFi.persistent(enabled);
}

void Esp32WifiManager::setAutoReconnect(bool enabled) {
    WiFi.setAutoReconnect(enabled);
}

void Esp32WifiManager::setAutoConnect(bool enabled) {
    WiFi.setAutoConnect(enabled);
}

void Esp32WifiManager::setTxPower(int8_t power) {
    // Map int8_t to wifi_power_t (ESP32 specific)
    WiFi.setTxPower(static_cast<wifi_power_t>(power));
}

void Esp32WifiManager::setSleepEnabled(bool enabled) {
    WiFi.setSleep(enabled);
}

bool Esp32WifiManager::beginSta(const char* ssid, const char* password) {
    if (password) {
        WiFi.begin(ssid, password);
    } else {
        WiFi.begin(ssid);
    }
    return true;
}

bool Esp32WifiManager::disconnectSta(bool wifiOff, bool eraseAp) {
    return WiFi.disconnect(wifiOff, eraseAp);
}

WifiStatus Esp32WifiManager::getStaStatus() const {
    wl_status_t status = WiFi.status();
    switch (status) {
        case WL_IDLE_STATUS:     return WifiStatus::IDLE;
        case WL_NO_SSID_AVAIL:   return WifiStatus::NO_SSID_AVAIL;
        case WL_SCAN_COMPLETED:  return WifiStatus::SCAN_COMPLETED;
        case WL_CONNECTED:       return WifiStatus::CONNECTED;
        case WL_CONNECT_FAILED:  return WifiStatus::CONNECT_FAILED;
        case WL_CONNECTION_LOST: return WifiStatus::CONNECTION_LOST;
        case WL_DISCONNECTED:    return WifiStatus::DISCONNECTED;
        default:                 return WifiStatus::IDLE;
    }
}

bool Esp32WifiManager::isStaConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

IpAddress Esp32WifiManager::getStaIp() const {
    IpAddress addr;
    IPAddress ip = WiFi.localIP();
    addr.octets[0] = ip[0];
    addr.octets[1] = ip[1];
    addr.octets[2] = ip[2];
    addr.octets[3] = ip[3];
    return addr;
}

int8_t Esp32WifiManager::getStaRssi() const {
    return WiFi.RSSI();
}

size_t Esp32WifiManager::getStaSsid(char* buffer, size_t bufferSize) const {
    String ssid = WiFi.SSID();
    size_t len = ssid.length();
    if (buffer && bufferSize > 0) {
        size_t copyLen = (len < bufferSize - 1) ? len : (bufferSize - 1);
        strncpy(buffer, ssid.c_str(), copyLen);
        buffer[copyLen] = '\0';
    }
    return len;
}

bool Esp32WifiManager::beginAp(const char* ssid, const char* password,
                               uint8_t channel, bool hidden) {
    return WiFi.softAP(ssid, password, channel, hidden);
}

bool Esp32WifiManager::stopAp() {
    return WiFi.softAPdisconnect(true);
}

IpAddress Esp32WifiManager::getApIp() const {
    IpAddress addr;
    IPAddress ip = WiFi.softAPIP();
    addr.octets[0] = ip[0];
    addr.octets[1] = ip[1];
    addr.octets[2] = ip[2];
    addr.octets[3] = ip[3];
    return addr;
}

size_t Esp32WifiManager::getApSsid(char* buffer, size_t bufferSize) const {
    String ssid = WiFi.softAPSSID();
    size_t len = ssid.length();
    if (buffer && bufferSize > 0) {
        size_t copyLen = (len < bufferSize - 1) ? len : (bufferSize - 1);
        strncpy(buffer, ssid.c_str(), copyLen);
        buffer[copyLen] = '\0';
    }
    return len;
}

uint8_t Esp32WifiManager::getApStationCount() const {
    return WiFi.softAPgetStationNum();
}

void Esp32WifiManager::onEvent(WifiEventCallback callback) {
    eventCallback_ = callback;

    // Register ESP32 WiFi event handler
    WiFi.onEvent([](WiFiEvent_t event) {
        if (!eventCallback_) return;

        WifiEvent halEvent;
        switch (event) {
            case ARDUINO_EVENT_WIFI_STA_START:
                halEvent = WifiEvent::STA_START; break;
            case ARDUINO_EVENT_WIFI_STA_STOP:
                halEvent = WifiEvent::STA_STOP; break;
            case ARDUINO_EVENT_WIFI_STA_CONNECTED:
                halEvent = WifiEvent::STA_CONNECTED; break;
            case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
                halEvent = WifiEvent::STA_DISCONNECTED; break;
            case ARDUINO_EVENT_WIFI_STA_GOT_IP:
                halEvent = WifiEvent::STA_GOT_IP; break;
            case ARDUINO_EVENT_WIFI_STA_LOST_IP:
                halEvent = WifiEvent::STA_LOST_IP; break;
            case ARDUINO_EVENT_WIFI_AP_START:
                halEvent = WifiEvent::AP_START; break;
            case ARDUINO_EVENT_WIFI_AP_STOP:
                halEvent = WifiEvent::AP_STOP; break;
            case ARDUINO_EVENT_WIFI_AP_STACONNECTED:
                halEvent = WifiEvent::AP_STA_CONNECTED; break;
            case ARDUINO_EVENT_WIFI_AP_STADISCONNECTED:
                halEvent = WifiEvent::AP_STA_DISCONNECTED; break;
            default:
                return;  // Unknown event, don't call callback
        }
        eventCallback_(halEvent);
    });
}

} // namespace hal

#endif // PLATFORM_ESP32
