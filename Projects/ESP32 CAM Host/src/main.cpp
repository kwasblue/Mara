#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"

#include "config/Wifisecrets.h"

// ====== CAMERA PIN CONFIG (AI Thinker ESP32-CAM) ======
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Onboard white LED "flash" (AI Thinker)
static constexpr int LED_FLASH_PIN = 4;

// ====== CameraServer class ======
class CameraServer {
public:
    explicit CameraServer(uint16_t port = 80)
        : server_(port) {}

    void begin() {
        Serial.println(F("[CAM] Booting CameraServer..."));

        pinMode(LED_FLASH_PIN, OUTPUT);
        digitalWrite(LED_FLASH_PIN, LOW);  // flash off by default

        setupCamera_();
        setupWifi_();

        server_.begin();
        Serial.println(F("[HTTP] Server started. Visit http://<ip>/ or /jpg"));
    }

    void loop() {
        WiFiClient client = server_.available();
        if (!client) {
            delay(5);
            return;
        }

        // Wait briefly for data
        uint32_t start = millis();
        while (!client.available() && (millis() - start) < 2000) {
            delay(1);
        }
        if (!client.available()) {
            client.stop();
            return;
        }

        handleClient_(client);
        client.stop();
    }

private:
    WiFiServer server_;

    void setupCamera_() {
        camera_config_t config;
        config.ledc_channel = LEDC_CHANNEL_0;
        config.ledc_timer   = LEDC_TIMER_0;
        config.pin_d0       = Y2_GPIO_NUM;
        config.pin_d1       = Y3_GPIO_NUM;
        config.pin_d2       = Y4_GPIO_NUM;
        config.pin_d3       = Y5_GPIO_NUM;
        config.pin_d4       = Y6_GPIO_NUM;
        config.pin_d5       = Y7_GPIO_NUM;
        config.pin_d6       = Y8_GPIO_NUM;
        config.pin_d7       = Y9_GPIO_NUM;
        config.pin_xclk     = XCLK_GPIO_NUM;
        config.pin_pclk     = PCLK_GPIO_NUM;
        config.pin_vsync    = VSYNC_GPIO_NUM;
        config.pin_href     = HREF_GPIO_NUM;
        config.pin_sccb_sda = SIOD_GPIO_NUM;
        config.pin_sccb_scl = SIOC_GPIO_NUM;
        config.pin_pwdn     = PWDN_GPIO_NUM;
        config.pin_reset    = RESET_GPIO_NUM;
        config.xclk_freq_hz = 20000000;
        config.pixel_format = PIXFORMAT_JPEG;

        // Resolution / quality
        config.frame_size   = FRAMESIZE_VGA;  // 640x480
        config.jpeg_quality = 10;             // 0–63 (lower = better)
        config.fb_count     = 2;

        esp_err_t err = esp_camera_init(&config);
        if (err != ESP_OK) {
            Serial.printf("[CAM] Camera init failed with error 0x%x\n", err);
            delay(2000);
            ESP.restart();
        }

        Serial.println(F("[CAM] Camera initialized"));
    }

    void setupWifi_() {
        Serial.println(F("[WIFI] Connecting..."));

        WiFi.mode(WIFI_STA);
        WiFi.begin(CAM_WIFI_SSID, CAM_WIFI_PASSWORD);

        uint32_t start = millis();
        const uint32_t timeoutMs = 15000;

        while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
            delay(500);
            Serial.print(".");
        }
        Serial.println();

        if (WiFi.status() == WL_CONNECTED) {
            Serial.print(F("[WIFI] Connected, IP: "));
            Serial.println(WiFi.localIP());
        } else {
            Serial.println(F("[WIFI] Failed to connect"));
        }
    }

    void sendJpeg_(WiFiClient &client) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println(F("[CAM] fb_get failed"));
            client.print("HTTP/1.1 500 Internal Server Error\r\n\r\n");
            return;
        }

        client.print("HTTP/1.1 200 OK\r\n");
        client.print("Content-Type: image/jpeg\r\n");
        client.printf("Content-Length: %u\r\n", fb->len);
        client.print("Connection: close\r\n");
        client.print("\r\n");

        client.write(fb->buf, fb->len);
        esp_camera_fb_return(fb);
    }

    void handleRoot_(WiFiClient &client) {
        client.print("HTTP/1.1 200 OK\r\n");
        client.print("Content-Type: text/html\r\n\r\n");
        client.print("<html><body><h1>ESP32-CAM</h1>");
        client.print("<p>Snapshot URL: <code>/jpg</code></p>");
        client.print("<img src=\"/jpg\" />");
        client.print("<p>Flash control: <a href=\"/flash_on\">ON</a> | <a href=\"/flash_off\">OFF</a></p>");
        client.print("</body></html>");
    }

    void handleClient_(WiFiClient &client) {
        // Read request line
        String req = client.readStringUntil('\r');
        client.readStringUntil('\n'); // consume '\n'

        // Skip headers
        while (client.available()) {
            String line = client.readStringUntil('\n');
            if (line == "\r" || line == "") break;
        }

        if (req.startsWith("GET /jpg")) {
            sendJpeg_(client);
        } else if (req.startsWith("GET /flash_on")) {
            digitalWrite(LED_FLASH_PIN, HIGH);
            client.print("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nFlash ON");
        } else if (req.startsWith("GET /flash_off")) {
            digitalWrite(LED_FLASH_PIN, LOW);
            client.print("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nFlash OFF");
        } else {
            handleRoot_(client);
        }
    }
};

// ====== Global instance ======
CameraServer g_cam;

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    Serial.println(F("[MCU] ESP32-CAM (PlatformIO) starting..."));

    g_cam.begin();
}

void loop() {
    g_cam.loop();
    delay(1); // tiny yield
}
