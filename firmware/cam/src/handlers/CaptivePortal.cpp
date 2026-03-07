#include "handlers/CaptivePortal.h"
#include "network/WebServer.h"
#include "utils/Logger.h"
#include <ArduinoJson.h>

static const char* TAG = "Captive";

const char CAPTIVE_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM WiFi Setup</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff;
               margin: 0; padding: 20px; min-height: 100vh; }
        .container { max-width: 400px; margin: 0 auto; }
        h1 { color: #4CAF50; text-align: center; }
        .logo { text-align: center; font-size: 48px; margin-bottom: 20px; }
        .card { background: #2d2d2d; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #888; }
        input, select { width: 100%; padding: 12px; background: #444; border: 1px solid #555;
                       border-radius: 4px; color: #fff; font-size: 16px; }
        .btn { width: 100%; background: #4CAF50; color: white; padding: 14px; border: none;
               border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        .btn:hover { background: #45a049; }
        .btn-secondary { background: #555; }
        .networks { margin-bottom: 20px; }
        .network { padding: 10px; background: #444; border-radius: 4px; margin-bottom: 5px;
                   cursor: pointer; display: flex; justify-content: space-between; }
        .network:hover { background: #555; }
        .signal { color: #4CAF50; }
        .loading { text-align: center; padding: 20px; }
        .status { padding: 10px; border-radius: 4px; margin-top: 10px; display: none; }
        .success { background: #4CAF50; }
        .error { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📷</div>
        <h1>ESP32-CAM Setup</h1>

        <div class="card">
            <h2>Available Networks</h2>
            <div id="networks" class="networks">
                <div class="loading">Scanning...</div>
            </div>
            <button class="btn btn-secondary" onclick="scanNetworks()">Refresh</button>
        </div>

        <div class="card">
            <form id="wifiForm" onsubmit="saveConfig(event)">
                <div class="form-group">
                    <label>WiFi Network (SSID)</label>
                    <input type="text" id="ssid" required placeholder="Enter network name">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" placeholder="Enter password">
                </div>
                <div class="form-group">
                    <label>Device Hostname</label>
                    <input type="text" id="hostname" value="esp32cam" pattern="[a-zA-Z0-9-]+"
                           title="Letters, numbers, and hyphens only">
                </div>
                <button type="submit" class="btn">Save & Connect</button>
            </form>
            <div class="status" id="status"></div>
        </div>
    </div>
    <script>
        function scanNetworks() {
            document.getElementById('networks').innerHTML = '<div class="loading">Scanning...</div>';
            fetch('/captive/scan')
                .then(r => r.json())
                .then(networks => {
                    const container = document.getElementById('networks');
                    if (networks.length === 0) {
                        container.innerHTML = '<div class="loading">No networks found</div>';
                        return;
                    }
                    container.innerHTML = networks.map(n =>
                        `<div class="network" onclick="selectNetwork('${n.ssid}')">
                            <span>${n.ssid}${n.secure ? ' 🔒' : ''}</span>
                            <span class="signal">${getSignalBars(n.rssi)}</span>
                        </div>`
                    ).join('');
                })
                .catch(() => {
                    document.getElementById('networks').innerHTML =
                        '<div class="loading">Scan failed. Try again.</div>';
                });
        }

        function getSignalBars(rssi) {
            if (rssi > -50) return '▂▄▆█';
            if (rssi > -60) return '▂▄▆_';
            if (rssi > -70) return '▂▄__';
            return '▂___';
        }

        function selectNetwork(ssid) {
            document.getElementById('ssid').value = ssid;
            document.getElementById('password').focus();
        }

        function saveConfig(e) {
            e.preventDefault();
            const status = document.getElementById('status');
            status.style.display = 'block';
            status.className = 'status';
            status.textContent = 'Saving...';

            fetch('/captive/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ssid: document.getElementById('ssid').value,
                    password: document.getElementById('password').value,
                    hostname: document.getElementById('hostname').value
                })
            })
            .then(r => r.json())
            .then(d => {
                if (d.success) {
                    status.className = 'status success';
                    status.textContent = 'Saved! Device will reboot and connect to WiFi.';
                    setTimeout(() => {
                        status.textContent += ' Redirecting in 10 seconds...';
                    }, 2000);
                } else {
                    status.className = 'status error';
                    status.textContent = d.error || 'Save failed';
                }
            })
            .catch(() => {
                status.className = 'status error';
                status.textContent = 'Connection error';
            });
        }

        // Initial scan
        scanNetworks();
    </script>
</body>
</html>
)rawliteral";

CaptivePortal::CaptivePortal(ConfigStore& config, WiFiManager& wifi)
    : config_(config), wifi_(wifi) {}

void CaptivePortal::registerHandlers(AsyncWebServer& server) {
    // Main captive portal page
    server.on("/captive", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handlePortalPage(request);
    });

    // Redirect common captive portal detection URLs
    server.on("/generate_204", HTTP_GET, [this](AsyncWebServerRequest* request) {
        request->redirect("/captive");
    });

    server.on("/hotspot-detect.html", HTTP_GET, [this](AsyncWebServerRequest* request) {
        request->redirect("/captive");
    });

    server.on("/connecttest.txt", HTTP_GET, [this](AsyncWebServerRequest* request) {
        request->redirect("/captive");
    });

    // Scan networks
    server.on("/captive/scan", HTTP_GET, [this](AsyncWebServerRequest* request) {
        handleScan(request);
    });

    // Save config
    server.on("/captive/save", HTTP_POST,
        [](AsyncWebServerRequest* request) {},
        nullptr,
        [this](AsyncWebServerRequest* request, uint8_t* data, size_t len, size_t index, size_t total) {
            if (index == 0 && len == total) {
                handleSaveConfig(request);
            }
        }
    );

    LOG_INFO(TAG, "Captive portal handlers registered");
}

void CaptivePortal::handlePortalPage(AsyncWebServerRequest* request) {
    request->send_P(200, "text/html", CAPTIVE_HTML);
}

void CaptivePortal::handleScan(AsyncWebServerRequest* request) {
    int n = WiFi.scanNetworks();

    JsonDocument doc;
    JsonArray networks = doc.to<JsonArray>();

    for (int i = 0; i < n && i < 20; i++) {
        JsonObject net = networks.add<JsonObject>();
        net["ssid"] = WiFi.SSID(i);
        net["rssi"] = WiFi.RSSI(i);
        net["secure"] = WiFi.encryptionType(i) != WIFI_AUTH_OPEN;
    }

    WiFi.scanDelete();

    String json;
    serializeJson(doc, json);
    WebServerManager::sendJson(request, 200, json);
}

void CaptivePortal::handleSaveConfig(AsyncWebServerRequest* request) {
    // Note: data comes from body handler, we need to use request params or store data
    // For simplicity, we'll use a static buffer approach
    static uint8_t bodyBuffer[512];
    static size_t bodyLen = 0;

    // This is called after body handler stores data
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, request->arg("plain"));

    if (error) {
        // Try to get from body directly if available
        WebServerManager::sendError(request, 400, "Invalid JSON");
        return;
    }

    NetworkConfig netConfig;
    config_.loadNetworkConfig(netConfig);

    const char* ssid = doc["ssid"] | "";
    const char* password = doc["password"] | "";
    const char* hostname = doc["hostname"] | "esp32cam";

    if (strlen(ssid) == 0) {
        WebServerManager::sendError(request, 400, "SSID required");
        return;
    }

    strncpy(netConfig.ssid, ssid, sizeof(netConfig.ssid) - 1);
    strncpy(netConfig.password, password, sizeof(netConfig.password) - 1);
    strncpy(netConfig.hostname, hostname, sizeof(netConfig.hostname) - 1);
    netConfig.configured = true;

    config_.saveNetworkConfig(netConfig);

    JsonDocument response;
    response["success"] = true;
    response["message"] = "Configuration saved. Rebooting...";

    String json;
    serializeJson(response, json);
    WebServerManager::sendJson(request, 200, json);

    // Schedule reboot
    delay(1000);
    ESP.restart();
}
