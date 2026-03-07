#pragma once

#include "esp_camera.h"

// ====== Default Camera Settings ======
#define DEFAULT_FRAME_SIZE      FRAMESIZE_VGA   // 640x480
#define DEFAULT_JPEG_QUALITY    12              // 0-63, lower = better quality
#define DEFAULT_FB_COUNT        3               // Frame buffer count (3 enables capture pipelining)

#define DEFAULT_BRIGHTNESS      0               // -2 to 2
#define DEFAULT_CONTRAST        0               // -2 to 2
#define DEFAULT_SATURATION      0               // -2 to 2
#define DEFAULT_SHARPNESS       0               // -2 to 2
#define DEFAULT_DENOISE         0               // 0-255
#define DEFAULT_SPECIAL_EFFECT  0               // 0-6
#define DEFAULT_WHITEBAL        1               // 0 = disable, 1 = enable
#define DEFAULT_AWB_GAIN        1               // 0 = disable, 1 = enable
#define DEFAULT_WB_MODE         0               // 0-4
#define DEFAULT_EXPOSURE_CTRL   1               // 0 = disable, 1 = enable
#define DEFAULT_AEC2            0               // 0 = disable, 1 = enable
#define DEFAULT_AE_LEVEL        0               // -2 to 2
#define DEFAULT_AEC_VALUE       300             // 0-1200
#define DEFAULT_GAIN_CTRL       1               // 0 = disable, 1 = enable
#define DEFAULT_AGC_GAIN        0               // 0-30
#define DEFAULT_GAINCEILING     0               // 0-6
#define DEFAULT_BPC             0               // 0 = disable, 1 = enable
#define DEFAULT_WPC             1               // 0 = disable, 1 = enable
#define DEFAULT_RAW_GMA         1               // 0 = disable, 1 = enable
#define DEFAULT_LENC            1               // 0 = disable, 1 = enable
#define DEFAULT_HMIRROR         0               // 0 = disable, 1 = enable
#define DEFAULT_VFLIP           0               // 0 = disable, 1 = enable
#define DEFAULT_DCW             1               // 0 = disable, 1 = enable
#define DEFAULT_COLORBAR        0               // 0 = disable, 1 = enable

// ====== Default Network Settings ======
#define DEFAULT_HOSTNAME        "esp32cam"
#define DEFAULT_AP_SSID         "ESP32-CAM-Setup"
#define DEFAULT_AP_PASSWORD     "camsetup123"
#define DEFAULT_AP_CHANNEL      1
#define DEFAULT_HTTP_PORT       80
#define DEFAULT_WIFI_TIMEOUT_MS 15000
#define DEFAULT_RECONNECT_INTERVAL_MS 5000

// ====== Default Motion Detection Settings ======
#define DEFAULT_MOTION_ENABLED      false
#define DEFAULT_MOTION_SENSITIVITY  30      // 0-100, higher = more sensitive
#define DEFAULT_MOTION_THRESHOLD    15      // Minimum pixel diff to count as change
#define DEFAULT_MOTION_COOLDOWN_MS  5000    // Time between motion events

// ====== Default Security Settings ======
#define DEFAULT_AUTH_ENABLED    true
#define DEFAULT_RATE_LIMIT      30          // Requests per minute for protected endpoints

// ====== Streaming Settings ======
#define MAX_STREAM_CLIENTS      3
#define STREAM_PART_BOUNDARY    "123456789000000000000987654321"

// Performance tuning
#define STREAM_TARGET_FPS       30              // Target FPS (adaptive timing)
#define STREAM_MIN_FRAME_MS     20              // Minimum ms between frames (~50 FPS max)
#define STREAM_QUALITY_SCALING  1               // Enable quality reduction with multiple clients
#define STREAM_QUALITY_PER_CLIENT 4             // Quality reduction per additional client (0-63 scale)
#define STREAM_MAX_QUALITY_REDUCTION 20         // Max quality reduction from base

// Frame skipping
#define STREAM_ENABLE_FRAME_SKIP 1              // Enable frame skipping under load
#define STREAM_SKIP_THRESHOLD_MS 100            // Skip frame if capture takes longer than this

// ====== Watchdog Settings ======
#define WATCHDOG_TIMEOUT_S      30          // Seconds before watchdog resets
