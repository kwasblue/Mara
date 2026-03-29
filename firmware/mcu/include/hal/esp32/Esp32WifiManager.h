// include/hal/esp32/Esp32WifiManager.h
// ESP32 WiFi manager implementation
#pragma once

#include <cstddef>
#include "../IWifiManager.h"

namespace hal {

/// ESP32 WiFi manager implementation wrapping ESP32 WiFi API.
class Esp32WifiManager : public IWifiManager {
public:
    Esp32WifiManager() = default;

    void setMode(WifiMode mode) override;
    WifiMode getMode() const override;
    void setPersistent(bool enabled) override;
    void setAutoReconnect(bool enabled) override;
    void setAutoConnect(bool enabled) override;
    void setTxPower(int8_t power) override;
    void setSleepEnabled(bool enabled) override;

    bool beginSta(const char* ssid, const char* password = nullptr) override;
    bool disconnectSta(bool wifiOff = false, bool eraseAp = false) override;
    WifiStatus getStaStatus() const override;
    bool isStaConnected() const override;
    IpAddress getStaIp() const override;
    int8_t getStaRssi() const override;
    size_t getStaSsid(char* buffer, size_t bufferSize) const override;

    bool beginAp(const char* ssid, const char* password = nullptr,
                uint8_t channel = 1, bool hidden = false) override;
    bool stopAp() override;
    IpAddress getApIp() const override;
    size_t getApSsid(char* buffer, size_t bufferSize) const override;
    uint8_t getApStationCount() const override;

    void onEvent(WifiEventCallback callback) override;

private:
    static WifiEventCallback eventCallback_;
};

} // namespace hal
