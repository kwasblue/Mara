#include <Arduino.h>

// Utils
#include "utils/Logger.h"
#include "utils/Watchdog.h"

// Config & Storage
#include "config/BoardConfig.h"
#include "config/DefaultSettings.h"
#include "storage/ConfigStore.h"

// Camera
#include "camera/CameraManager.h"
#include "camera/MotionDetector.h"

// Network
#include "network/WiFiManager.h"
#include "network/WebServer.h"
#include "network/StreamHandler.h"
#include "network/MjpegServer.h"
#include "network/OTAHandler.h"

// Handlers
#include "handlers/PageHandlers.h"
#include "handlers/ApiHandlers.h"
#include "handlers/CaptivePortal.h"

static const char* TAG = "Main";

// Global instances
ConfigStore g_configStore;
CameraManager g_camera;
MotionDetector g_motionDetector;
WiFiManager g_wifiManager;
WebServerManager g_webServer;
StreamHandler g_streamHandler(g_camera);
MjpegServer g_mjpegServer(g_camera);
OTAHandler g_otaHandler;
PageHandlers* g_pageHandlers = nullptr;
ApiHandlers* g_apiHandlers = nullptr;
CaptivePortal* g_captivePortal = nullptr;

// Configuration structures
CameraConfig g_cameraConfig;
NetworkConfig g_networkConfig;
MotionConfig g_motionConfig;
SecurityConfig g_securityConfig;

// Motion detection callback
void onMotionDetected() {
    LOG_INFO(TAG, "Motion detected!");
    // Could trigger recording, send notification, etc.
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    LOG_INFO(TAG, "ESP32-CAM Starting...");
    LOG_INFO(TAG, "Free heap: %d bytes", ESP.getFreeHeap());

    // Initialize watchdog
    if (Watchdog::init(WATCHDOG_TIMEOUT_S)) {
        LOG_INFO(TAG, "Watchdog initialized (%ds timeout)", WATCHDOG_TIMEOUT_S);
    }

    // Initialize config store
    g_configStore.begin();

    // Load configurations
    g_configStore.loadCameraConfig(g_cameraConfig);
    g_configStore.loadNetworkConfig(g_networkConfig);
    g_configStore.loadMotionConfig(g_motionConfig);
    g_configStore.loadSecurityConfig(g_securityConfig);

    // Initialize camera
    if (!g_camera.begin()) {
        LOG_ERROR(TAG, "Camera init failed!");
        delay(3000);
        ESP.restart();
    }

    // Apply camera settings
    g_camera.applyConfig(g_cameraConfig);

    // Initialize motion detector
    g_motionDetector.configure(g_motionConfig);
    g_motionDetector.setCallback(onMotionDetected);

    // Initialize WiFi
    g_wifiManager.begin(g_networkConfig);

    // Wait for WiFi connection or AP mode
    uint32_t wifiStart = millis();
    while (!g_wifiManager.isConnected() && !g_wifiManager.isAPMode()) {
        g_wifiManager.loop();
        Watchdog::feed();
        delay(100);

        if (millis() - wifiStart > DEFAULT_WIFI_TIMEOUT_MS + 5000) {
            break;
        }
    }

    // Initialize web server
    g_webServer.begin();
    AsyncWebServer& server = g_webServer.getServer();
    AuthMiddleware& auth = g_webServer.getAuth();

    // Configure auth
    auth.setEnabled(g_securityConfig.authEnabled);
    auth.setRateLimit(g_securityConfig.rateLimit);

    // Register handlers
    g_streamHandler.registerHandlers(server);
    g_otaHandler.registerHandlers(server, true);

    // Start dedicated MJPEG stream server on port 81
    if (!g_mjpegServer.start(81)) {
        LOG_ERROR(TAG, "Failed to start MJPEG server on port 81");
    }

    // Create and register page handlers
    g_pageHandlers = new PageHandlers(g_camera, g_wifiManager);
    g_pageHandlers->registerHandlers(server);

    // Create and register API handlers
    g_apiHandlers = new ApiHandlers(g_camera, g_motionDetector, g_wifiManager, g_configStore, auth);
    g_apiHandlers->registerHandlers(server);

    // Create and register captive portal
    g_captivePortal = new CaptivePortal(g_configStore, g_wifiManager);
    g_captivePortal->registerHandlers(server);

    // If in AP mode, activate captive portal
    if (g_wifiManager.isAPMode()) {
        g_captivePortal->setActive(true);
        LOG_INFO(TAG, "Captive portal active");
    }

    LOG_INFO(TAG, "=================================");
    LOG_INFO(TAG, "ESP32-CAM Ready!");
    LOG_INFO(TAG, "IP: %s", g_wifiManager.getIP().toString().c_str());
    LOG_INFO(TAG, "Hostname: %s.local", g_wifiManager.getHostname());
    LOG_INFO(TAG, "Dashboard: http://%s/", g_wifiManager.getIP().toString().c_str());
    LOG_INFO(TAG, "Snapshot: http://%s/jpg", g_wifiManager.getIP().toString().c_str());
    LOG_INFO(TAG, "Stream: http://%s:81/stream", g_wifiManager.getIP().toString().c_str());
    LOG_INFO(TAG, "=================================");
    LOG_INFO(TAG, "Free heap: %d bytes", ESP.getFreeHeap());
}

void loop() {
    // Feed watchdog
    Watchdog::feed();

    // Handle WiFi reconnection
    g_wifiManager.loop();

    // Process motion detection if enabled
    if (g_motionDetector.isEnabled() && g_mjpegServer.getActiveStreams() == 0) {
        // Only check motion when not streaming (to save resources)
        static uint32_t lastMotionCheck = 0;
        uint32_t now = millis();

        if (now - lastMotionCheck > 500) {  // Check every 500ms
            lastMotionCheck = now;
            camera_fb_t* fb = g_camera.capture();
            if (fb) {
                g_motionDetector.processFrame(fb);
                g_camera.release(fb);
            }
        }
    }

    // Small yield
    delay(1);
}
