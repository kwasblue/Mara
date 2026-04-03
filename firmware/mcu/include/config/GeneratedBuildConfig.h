// GeneratedBuildConfig.h
// =============================================================================
// AUTO-GENERATED FILE - DO NOT EDIT
// =============================================================================
// Generated from: config/mara_build.yaml
// Generated at:   2026-04-03T01:30:19.486537
// Active profile: full
//
// To regenerate, run:
//   mara generate all
// =============================================================================

#pragma once

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
