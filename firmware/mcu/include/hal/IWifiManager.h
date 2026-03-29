// include/hal/IWifiManager.h
// Abstract WiFi manager interface.
// Abstracts ESP32 WiFi API for platform portability.
#pragma once

#include <cstddef>
#include <cstdint>

namespace hal {

/// WiFi operating mode
enum class WifiMode : uint8_t {
    OFF = 0,
    STA = 1,     // Station mode (client)
    AP = 2,      // Access point mode
    AP_STA = 3   // Both AP and STA simultaneously
};

/// WiFi connection status
enum class WifiStatus : uint8_t {
    IDLE = 0,
    NO_SSID_AVAIL = 1,
    SCAN_COMPLETED = 2,
    CONNECTED = 3,
    CONNECT_FAILED = 4,
    CONNECTION_LOST = 5,
    DISCONNECTED = 6
};

/// WiFi event types
enum class WifiEvent : uint8_t {
    STA_START = 0,
    STA_STOP = 1,
    STA_CONNECTED = 2,
    STA_DISCONNECTED = 3,
    STA_GOT_IP = 4,
    STA_LOST_IP = 5,
    AP_START = 6,
    AP_STOP = 7,
    AP_STA_CONNECTED = 8,
    AP_STA_DISCONNECTED = 9
};

/// WiFi event callback signature
using WifiEventCallback = void (*)(WifiEvent event);

/// IP address representation (platform-independent)
struct IpAddress {
    uint8_t octets[4] = {0, 0, 0, 0};

    uint32_t toUint32() const {
        return (octets[0]) | (octets[1] << 8) | (octets[2] << 16) | (octets[3] << 24);
    }

    void fromUint32(uint32_t ip) {
        octets[0] = ip & 0xFF;
        octets[1] = (ip >> 8) & 0xFF;
        octets[2] = (ip >> 16) & 0xFF;
        octets[3] = (ip >> 24) & 0xFF;
    }
};

/// Abstract WiFi manager interface.
/// Platform implementations wrap ESP32 WiFi, etc.
///
/// Usage:
///   IWifiManager* wifi = hal.wifi;
///   wifi->setMode(WifiMode::AP_STA);
///   wifi->beginSta("MySSID", "MyPassword");
///   wifi->beginAp("RobotAP", "robotpass");
///   // In loop:
///   if (wifi->isStaConnected()) { ... }
class IWifiManager {
public:
    virtual ~IWifiManager() = default;

    // =========================================================================
    // Configuration
    // =========================================================================

    /// Set WiFi operating mode
    virtual void setMode(WifiMode mode) = 0;

    /// Get current WiFi mode
    virtual WifiMode getMode() const = 0;

    /// Enable/disable persistent WiFi settings (saved to NVS)
    virtual void setPersistent(bool enabled) = 0;

    /// Enable/disable auto-reconnect on disconnect
    virtual void setAutoReconnect(bool enabled) = 0;

    /// Enable/disable auto-connect on boot
    virtual void setAutoConnect(bool enabled) = 0;

    /// Set transmit power (platform-specific values)
    virtual void setTxPower(int8_t power) = 0;

    /// Enable/disable WiFi sleep mode
    virtual void setSleepEnabled(bool enabled) = 0;

    // =========================================================================
    // Station (STA) mode
    // =========================================================================

    /// Begin station mode connection
    /// @param ssid Network SSID
    /// @param password Network password (nullptr for open networks)
    /// @return true if connection initiated
    virtual bool beginSta(const char* ssid, const char* password = nullptr) = 0;

    /// Disconnect from station
    /// @param wifiOff Also disable WiFi radio
    /// @param eraseAp Erase saved AP credentials
    virtual bool disconnectSta(bool wifiOff = false, bool eraseAp = false) = 0;

    /// Get station connection status
    virtual WifiStatus getStaStatus() const = 0;

    /// Check if station is connected
    virtual bool isStaConnected() const = 0;

    /// Get station IP address
    virtual IpAddress getStaIp() const = 0;

    /// Get station RSSI (signal strength in dBm)
    virtual int8_t getStaRssi() const = 0;

    /// Get connected SSID
    /// @param buffer Buffer to store SSID
    /// @param bufferSize Size of buffer
    /// @return Actual SSID length
    virtual size_t getStaSsid(char* buffer, size_t bufferSize) const = 0;

    // =========================================================================
    // Access Point (AP) mode
    // =========================================================================

    /// Start access point
    /// @param ssid AP SSID
    /// @param password AP password (nullptr for open network)
    /// @param channel WiFi channel (1-13)
    /// @param hidden Hide SSID in broadcasts
    /// @return true if AP started
    virtual bool beginAp(const char* ssid, const char* password = nullptr,
                        uint8_t channel = 1, bool hidden = false) = 0;

    /// Stop access point
    virtual bool stopAp() = 0;

    /// Get AP IP address
    virtual IpAddress getApIp() const = 0;

    /// Get AP SSID
    /// @param buffer Buffer to store SSID
    /// @param bufferSize Size of buffer
    /// @return Actual SSID length
    virtual size_t getApSsid(char* buffer, size_t bufferSize) const = 0;

    /// Get number of stations connected to AP
    virtual uint8_t getApStationCount() const = 0;

    // =========================================================================
    // Events
    // =========================================================================

    /// Register event callback
    virtual void onEvent(WifiEventCallback callback) = 0;
};

/// Convert WifiStatus to string
inline const char* wifiStatusToString(WifiStatus status) {
    switch (status) {
        case WifiStatus::IDLE:            return "idle";
        case WifiStatus::NO_SSID_AVAIL:   return "no_ssid";
        case WifiStatus::SCAN_COMPLETED:  return "scan_completed";
        case WifiStatus::CONNECTED:       return "connected";
        case WifiStatus::CONNECT_FAILED:  return "connect_failed";
        case WifiStatus::CONNECTION_LOST: return "connection_lost";
        case WifiStatus::DISCONNECTED:    return "disconnected";
        default:                          return "unknown";
    }
}

/// Convert WifiMode to string
inline const char* wifiModeToString(WifiMode mode) {
    switch (mode) {
        case WifiMode::OFF:    return "off";
        case WifiMode::STA:    return "sta";
        case WifiMode::AP:     return "ap";
        case WifiMode::AP_STA: return "ap_sta";
        default:               return "unknown";
    }
}

} // namespace hal
