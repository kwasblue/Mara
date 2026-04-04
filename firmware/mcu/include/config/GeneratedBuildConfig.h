// GeneratedBuildConfig.h
// =============================================================================
// AUTO-GENERATED FILE - DO NOT EDIT
// =============================================================================
// Generated from: config/mara_build.yaml
// Generated at:   2026-04-04T13:18:08.602025
// Active profile: full
// Target platform: esp32
//
// To regenerate, run:
//   mara generate all
//
// Note: PLATFORM_* and HAS_* macros use #ifndef guards to allow
// command-line overrides (e.g., -DPLATFORM_NATIVE=1 for unit tests).
// =============================================================================

#pragma once

// =============================================================================
// Target Platform
// =============================================================================
// Only one PLATFORM_* should be 1, all others should be 0.
// This controls HAL selection via hal/PlatformHal.h
//
// For native/unit test builds, PLATFORM_NATIVE should be set via build flags
// which take precedence over these generated defaults.
#ifndef PLATFORM_ESP32
#define PLATFORM_ESP32 1
#endif
#ifndef PLATFORM_STM32
#define PLATFORM_STM32 0
#endif
#ifndef PLATFORM_RP2040
#define PLATFORM_RP2040 0
#endif
#ifndef PLATFORM_NATIVE
#define PLATFORM_NATIVE 0
#endif

#define MARA_PLATFORM_TARGET "esp32"
#define MARA_PLATFORM_BOARD "esp32dev"
#define MARA_PLATFORM_SDK "arduino"
#define MARA_PLATFORM_VARIANT ""

// =============================================================================
// Transport Settings
// =============================================================================
#define MARA_BAUD_RATE 921600
#define MARA_UPLOAD_BAUD_RATE 460800
#define MARA_TCP_PORT 3333
#define MARA_DEVICE_NAME "ESP32-bot"

// =============================================================================
// Feature Flags (profile: full)
// =============================================================================
// Transport
#ifndef HAS_WIFI
#define HAS_WIFI 1
#endif
#ifndef HAS_BLE
#define HAS_BLE 1
#endif
#ifndef HAS_UART_TRANSPORT
#define HAS_UART_TRANSPORT 1
#endif
#ifndef HAS_MQTT_TRANSPORT
#define HAS_MQTT_TRANSPORT 1
#endif

// Motors
#ifndef HAS_SERVO
#define HAS_SERVO 1
#endif
#ifndef HAS_STEPPER
#define HAS_STEPPER 1
#endif
#ifndef HAS_DC_MOTOR
#define HAS_DC_MOTOR 1
#endif
#ifndef HAS_ENCODER
#define HAS_ENCODER 1
#endif
#ifndef HAS_MOTION_CONTROLLER
#define HAS_MOTION_CONTROLLER 1
#endif

// Sensors
#ifndef HAS_ULTRASONIC
#define HAS_ULTRASONIC 1
#endif
#ifndef HAS_IMU
#define HAS_IMU 1
#endif
#ifndef HAS_LIDAR
#define HAS_LIDAR 1
#endif

// Control
#ifndef HAS_SIGNAL_BUS
#define HAS_SIGNAL_BUS 1
#endif
#ifndef HAS_CONTROL_KERNEL
#define HAS_CONTROL_KERNEL 1
#endif
#ifndef HAS_PID_CONTROLLER
#define HAS_PID_CONTROLLER 1
#endif
#ifndef HAS_STATE_SPACE
#define HAS_STATE_SPACE 1
#endif
#ifndef HAS_OBSERVER
#define HAS_OBSERVER 1
#endif
#ifndef HAS_CONTROL_MODULE
#define HAS_CONTROL_MODULE 1
#endif

// System
#ifndef HAS_OTA
#define HAS_OTA 1
#endif
#ifndef HAS_TELEMETRY
#define HAS_TELEMETRY 1
#endif
#ifndef HAS_HEARTBEAT
#define HAS_HEARTBEAT 1
#endif
#ifndef HAS_LOGGING
#define HAS_LOGGING 1
#endif
#ifndef HAS_IDENTITY
#define HAS_IDENTITY 1
#endif

// Audio
#ifndef HAS_AUDIO
#define HAS_AUDIO 0
#endif

// Debug
#ifndef HAS_BENCHMARK
#define HAS_BENCHMARK 1
#endif

// Active profile name
#define MARA_BUILD_PROFILE "full"

// =============================================================================
// Resource Limits
// =============================================================================
#define MARA_MAX_CONTROL_SLOTS 8
#define MARA_MAX_GRAPH_SLOTS 8
#define MARA_MAX_INPUTS 2
#define MARA_MAX_OBSERVERS 4
#define MARA_MAX_OUTPUTS 4
#define MARA_MAX_SIGNALS 128
#define MARA_MAX_STATES 6
