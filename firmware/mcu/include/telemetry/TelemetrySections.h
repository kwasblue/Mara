// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from TELEMETRY_SECTIONS in platform_schema.py
//
// Binary telemetry section IDs for structured sensor data.
// Use with registerBinProvider(section_id, ...) in TelemetryManager.

#pragma once

#include <cstdint>

namespace TelemetrySections {

// Section IDs (must match Python telemetry_sections.py)
enum class SectionId : uint8_t {
    TELEM_IMU            = 0x01,  // IMU sensor data (accel, gyro, temp)
    TELEM_ULTRASONIC     = 0x02,  // Ultrasonic distance sensor
    TELEM_LIDAR          = 0x03,  // LiDAR distance sensor
    TELEM_ENCODER0       = 0x04,  // Encoder 0 tick count
    TELEM_STEPPER0       = 0x05,  // Stepper motor 0 state
    TELEM_DC_MOTOR0      = 0x06,  // DC motor 0 state
    TELEM_CTRL_SIGNALS   = 0x10,  // Control signal bus values
    TELEM_CTRL_OBSERVERS = 0x11,  // Observer state estimates
    TELEM_CTRL_SLOTS     = 0x12,  // Control slot status
};

// Helper to get section ID as raw byte
inline uint8_t id(SectionId s) {
    return static_cast<uint8_t>(s);
}

// -----------------------------------------------------------------------------
// Section Formats (for reference)
// All multi-byte values are little-endian
// -----------------------------------------------------------------------------
//
// TELEM_IMU: online(u8) ok(u8) ax(i16) ay(i16) az(i16) gx(i16) gy(i16) gz(i16) temp(i16)
//   Size: 18 bytes
//
// TELEM_ULTRASONIC: sensor_id(u8) attached(u8) ok(u8) dist_mm(u16)
//   Size: 5 bytes
//
// TELEM_LIDAR: online(u8) ok(u8) dist_mm(u16) signal(u16)
//   Size: 6 bytes
//
// TELEM_ENCODER0: ticks(i32)
//   Size: 4 bytes
//
// TELEM_STEPPER0: motor_id(i8) attached(u8) enabled(u8) moving(u8) dir(u8) steps(i32) speed(i16)
//   Size: 11 bytes
//
// TELEM_DC_MOTOR0: attached(u8) speed_centi(i16)
//   Size: 3 bytes
//
// TELEM_CTRL_SIGNALS: count(u16) [id(u16) value(f32) ts_ms(u32)]*
//   Size: variable
//
// TELEM_CTRL_OBSERVERS: slot_count(u8) [slot(u8) enabled(u8) num_states(u8) states(f32)*]*
//   Size: variable
//
// TELEM_CTRL_SLOTS: slot_count(u8) [slot(u8) enabled(u8) ok(u8) run_count(u32)]*
//   Size: variable
//

} // namespace TelemetrySections
