#pragma once

// ====== AI Thinker ESP32-CAM Pin Definitions ======

// Camera power and reset
#define CAM_PIN_PWDN    32
#define CAM_PIN_RESET   -1

// Camera clock
#define CAM_PIN_XCLK    0

// Camera I2C (SCCB)
#define CAM_PIN_SIOD    26
#define CAM_PIN_SIOC    27

// Camera data pins (D0-D7)
#define CAM_PIN_D0      5
#define CAM_PIN_D1      18
#define CAM_PIN_D2      19
#define CAM_PIN_D3      21
#define CAM_PIN_D4      36
#define CAM_PIN_D5      39
#define CAM_PIN_D6      34
#define CAM_PIN_D7      35

// Camera sync pins
#define CAM_PIN_VSYNC   25
#define CAM_PIN_HREF    23
#define CAM_PIN_PCLK    22

// Onboard flash LED (active high)
#define LED_FLASH_PIN   4

// Onboard red LED (active low on some boards)
#define LED_STATUS_PIN  33

// SD card pins (directly on board, directly conflicts with flash LED)
#define SD_MMC_CLK      14
#define SD_MMC_CMD      15
#define SD_MMC_D0       2

// Camera clock frequency
#define CAM_XCLK_FREQ   20000000  // 20MHz
