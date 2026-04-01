// GeneratedBuildConfig.h
// =============================================================================
// AUTO-GENERATED FILE - DO NOT EDIT
// =============================================================================
// Generated from: config/mara_build.yaml
// Generated at:   2026-04-01T16:18:09.623790
// Active profile: full
//
// To regenerate, run:
//   python -m mara_host.tools.generate_all
// =============================================================================

#pragma once

// =============================================================================
// Transport Settings
// =============================================================================
#define MARA_BAUD_RATE 921600
#define MARA_TCP_PORT 3333
#define MARA_DEVICE_NAME "ESP32-bot"

// =============================================================================
// Feature Flags (profile: full)
// =============================================================================
// Transport
#define HAS_WIFI 1
#define HAS_BLE 1
#define HAS_UART_TRANSPORT 1
#define HAS_MQTT_TRANSPORT 1

// Motors
#define HAS_SERVO 1
#define HAS_STEPPER 1
#define HAS_DC_MOTOR 1
#define HAS_ENCODER 1
#define HAS_MOTION_CONTROLLER 1

// Sensors
#define HAS_ULTRASONIC 1
#define HAS_IMU 1
#define HAS_LIDAR 1

// Control
#define HAS_SIGNAL_BUS 1
#define HAS_CONTROL_KERNEL 1
#define HAS_PID_CONTROLLER 1
#define HAS_STATE_SPACE 1
#define HAS_OBSERVER 1
#define HAS_CONTROL_MODULE 1

// System
#define HAS_OTA 1
#define HAS_TELEMETRY 1
#define HAS_HEARTBEAT 1
#define HAS_LOGGING 1
#define HAS_IDENTITY 1

// Audio
#define HAS_AUDIO 0

// Debug
#define HAS_BENCHMARK 1

// Active profile name
#define MARA_BUILD_PROFILE "full"
