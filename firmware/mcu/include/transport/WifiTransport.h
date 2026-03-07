// core/WifiTransport.h
#pragma once

#include "config/FeatureFlags.h"

#if HAS_WIFI

#include <Arduino.h>
#include <WiFi.h>      // ESP32 WiFi
#include <vector>
#include "core/ITransport.h"
#include "core/Protocol.h"

class WifiTransport : public ITransport {
public:
    explicit WifiTransport(uint16_t port)
        : server_(port),
          port_(port) {}

    void begin() override {
        // Assumes WiFi already configured elsewhere (SSID/password, mode)
        server_.begin();
        rxBuffer_.clear();
        rxBuffer_.reserve(256);

        // Figure out which IP we actually have
        IPAddress sta = WiFi.localIP();
        IPAddress ap  = WiFi.softAPIP();

        Serial.println("[WifiTransport] begin()");
        Serial.printf("  [WifiTransport] STA IP: %s\n", sta.toString().c_str());
        Serial.printf("  [WifiTransport] AP  IP: %s\n", ap.toString().c_str());

        IPAddress listenIp = sta;
        if (listenIp.toString() == String("0.0.0.0")) {
            // fall back to AP IP if STA not connected
            listenIp = ap;
        }

        Serial.printf("  [WifiTransport] listening on %s:%u\n",
                      listenIp.toString().c_str(), port_);
    }

void loop() override {
    // Accept / monitor client
    if (!client_ || !client_.connected()) {
        // If we previously had a client and it disconnected, log it
        if (client_) {
            Serial.println("[WifiTransport] client disconnected");
            client_.stop();
        }

        WiFiClient newClient = server_.available();
        if (newClient) {
            client_ = newClient;
            Serial.printf(
                "[WifiTransport] client connected from %s:%u\n",
                client_.remoteIP().toString().c_str(),
                client_.remotePort()
            );
        }
        return;
    }

    // 🔹 Debug: send a simple heartbeat over WiFi every second
    // static uint32_t lastDebugMs = 0;
    // uint32_t now = millis();
    // if (now - lastDebugMs > 1000) {
    //     const char* dbg = "[WifiTransport] hello over WiFi\n";
    //     client_.write((const uint8_t*)dbg, strlen(dbg));
    //     lastDebugMs = now;
    // }

    // Read bytes from client
    while (client_.available() > 0) {
        uint8_t b = static_cast<uint8_t>(client_.read());
        rxBuffer_.push_back(b);
    }

    // Frame extraction
    if (handler_) {
        Protocol::extractFrames(
            rxBuffer_,
            [this](const uint8_t* frame, size_t len) {
                handler_(frame, len);
            }
        );
    }
}

    bool sendBytes(const uint8_t* data, size_t len) override {
        if (!client_ || !client_.connected()) {
            // Optional debug:
            //Serial.println("[WifiTransport] sendBytes(): no connected client");
            return false;
        }
        size_t written = client_.write(data, len);
        // Optional:
        // Serial.printf("[WifiTransport] sendBytes(): wrote %u/%u bytes\n",
        //               (unsigned)written, (unsigned)len);
        return written == len;
    }

private:
    WiFiServer           server_;
    WiFiClient           client_;
    std::vector<uint8_t> rxBuffer_;
    uint16_t             port_;
};

// example code for setupwifi()

//#include <WiFi.h>
// void setupWifi() {
//     WiFi.mode(WIFI_STA);
//     WiFi.begin("YourHomeSSID", "YourHomePassword");
//     Serial.print("[WiFi] Connecting");
//     while (WiFi.status() != WL_CONNECTED) {
//         delay(500);
//         Serial.print(".");
//     }
//     Serial.println();
//     Serial.print("[WiFi] Connected, IP: ");
//     Serial.println(WiFi.localIP());
// }

// const char* WIFI_SSID = "RobotAP";
// const char* WIFI_PASS = "robotpass";  // change to whatever

// void setupWifi() {
//     WiFi.mode(WIFI_AP);
//     WiFi.softAP(WIFI_SSID, WIFI_PASS);
//     IPAddress ip = WiFi.softAPIP();
//     Serial.print("[WiFi] AP started, IP: ");
//     Serial.println(ip);
// }

#else // !HAS_WIFI

#include "core/ITransport.h"

// Stub when WiFi is disabled
class WifiTransport : public ITransport {
public:
    explicit WifiTransport(uint16_t) {}
    void begin() override {}
    void loop() override {}
    bool sendBytes(const uint8_t*, size_t) override { return true; }
};

#endif // HAS_WIFI
