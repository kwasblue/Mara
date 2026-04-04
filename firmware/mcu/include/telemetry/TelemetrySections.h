// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from TELEMETRY_SECTIONS in schema.py
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
    TELEM_PERF           = 0x07,  // MCU performance and watchdog metrics
    TELEM_SENSOR_HEALTH  = 0x08,  // Compact sensor health and degraded-state summary
    TELEM_CTRL_SIGNALS   = 0x10,  // Control signal bus values
    TELEM_CTRL_OBSERVERS = 0x11,  // Observer state estimates
    TELEM_CTRL_SLOTS     = 0x12,  // Control slot status
    TELEM_BENCHMARK      = 0x13,  // Benchmark system state and latest results
    TELEM_SIGNAL_TRACE   = 0x14,  // Signal trace subscription (up to 16 signals)
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
// TELEM_IMU: online(u8) ok(u8) ax_mg(i16) ay_mg(i16) az_mg(i16) gx_mdps(i16) gy_mdps(i16) gz_mdps(i16) temp_c_centi(i16)
//   Size: 16 bytes
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
// TELEM_STEPPER0: motor_id(i8) attached(u8) enabled(u8) moving(u8) dir_forward(u8) last_cmd_steps(i32) speed_centi(i16)
//   Size: 11 bytes
//
// TELEM_DC_MOTOR0: attached(u8) speed_centi(i16)
//   Size: 3 bytes
//
// TELEM_PERF: last_fault(u8) hb_count(u32) hb_timeouts(u32) hb_recoveries(u32) hb_max_gap_ms(u32) motion_cmds(u32) motion_timeouts(u32) motion_max_gap_ms(u32) iterations(u32) overruns(u32) avg_total_us(u16) peak_total_us(u16) pkt_last_bytes(u16) pkt_max_bytes(u16) pkt_sent(u32) pkt_bytes(u32) pkt_dropped_sections(u32) pkt_last_sections(u8) pkt_max_sections(u8) pkt_buffered(u8)
//   Size: 60 bytes
//
// TELEM_SENSOR_HEALTH: 
//   Size: variable
//
// TELEM_CTRL_SIGNALS: 
//   Size: variable
//
// TELEM_CTRL_OBSERVERS: 
//   Size: variable
//
// TELEM_CTRL_SLOTS: 
//   Size: variable
//
// TELEM_BENCHMARK: bench_state(u8) active_test(u8) queue_depth(u8) result_count(u8)
//   Size: variable
//
// TELEM_SIGNAL_TRACE: 
//   Size: variable
//

} // namespace TelemetrySections
