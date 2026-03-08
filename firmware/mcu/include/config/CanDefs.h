// AUTO-GENERATED FILE — DO NOT EDIT BY HAND
// Generated from CAN_MESSAGES in schema.py
//
// CAN bus message definitions for hybrid real-time/protocol transport.

#pragma once

#include <cstdint>
#include <cstring>

namespace can {

// =============================================================================
// CONFIGURATION
// =============================================================================

constexpr uint8_t MAX_NODE_ID = 15;
constexpr uint8_t BROADCAST_ID = 0x0F;
constexpr uint32_t DEFAULT_BAUD_RATE = 500000;
constexpr size_t PROTO_PAYLOAD_SIZE = 6;
constexpr size_t PROTO_MAX_FRAMES = 16;
constexpr size_t PROTO_MAX_MSG_SIZE = 96;

// =============================================================================
// MESSAGE IDS
// =============================================================================

namespace MsgId {
    constexpr uint16_t ESTOP = 0x000;
    constexpr uint16_t SYNC = 0x001;
    constexpr uint16_t HEARTBEAT_BASE = 0x010;
    constexpr uint16_t SET_VEL_BASE = 0x020;
    constexpr uint16_t SET_SIGNAL_BASE = 0x030;
    constexpr uint16_t STOP_BASE = 0x040;
    constexpr uint16_t ARM_BASE = 0x050;
    constexpr uint16_t DISARM_BASE = 0x060;
    constexpr uint16_t ENCODER_BASE = 0x100;
    constexpr uint16_t IMU_ACCEL_BASE = 0x110;
    constexpr uint16_t IMU_GYRO_BASE = 0x120;
    constexpr uint16_t ANALOG_BASE = 0x130;
    constexpr uint16_t STATUS_BASE = 0x200;
    constexpr uint16_t ERROR_BASE = 0x210;
    constexpr uint16_t TELEM_BASE = 0x220;
    constexpr uint16_t PROTO_CMD_BASE = 0x300;
    constexpr uint16_t PROTO_RSP_BASE = 0x310;
    constexpr uint16_t PROTO_ACK_BASE = 0x320;
    constexpr uint16_t CONFIG_BASE = 0x400;
    constexpr uint16_t IDENTIFY_BASE = 0x410;
}

// Helper to build message ID with node
inline constexpr uint16_t makeId(uint16_t base, uint8_t nodeId) {
    return base | (nodeId & 0x0F);
}

// Extract node ID from message ID
inline constexpr uint8_t extractNodeId(uint16_t msgId) {
    return msgId & 0x0F;
}

// =============================================================================
// NODE STATE ENUM
// =============================================================================

enum class NodeState : uint8_t {
    INIT = 0,
    IDLE = 1,
    ARMED = 2,
    ACTIVE = 3,
    ERROR = 4,
    ESTOPPED = 5,
    RECOVERING = 6,
};

// =============================================================================
// PACKED MESSAGE STRUCTURES
// =============================================================================

#pragma pack(push, 1)

// Set velocity command (CAN-native, 8 bytes)
struct SetVelMsg {
    int16_t vx_mm_s;  // m/s
    int16_t omega_mrad_s;  // rad/s
    uint16_t flags;
    uint16_t seq;
};
static_assert(sizeof(SetVelMsg) == 8, "SetVelMsg size mismatch");

// Set signal value (CAN-native, 8 bytes)
struct SetSignalMsg {
    uint16_t signal_id;
    float value;
    uint16_t reserved;
};
static_assert(sizeof(SetSignalMsg) == 8, "SetSignalMsg size mismatch");

// Node heartbeat (CAN-native, 8 bytes)
struct HeartbeatMsg {
    uint32_t uptime_ms;
    uint8_t state;
    uint8_t load_pct;
    uint16_t errors;
};
static_assert(sizeof(HeartbeatMsg) == 8, "HeartbeatMsg size mismatch");

// Encoder counts and velocity (CAN-native, 8 bytes)
struct EncoderMsg {
    int32_t counts;
    int16_t velocity;  // counts/s
    uint16_t timestamp;  // ms
};
static_assert(sizeof(EncoderMsg) == 8, "EncoderMsg size mismatch");

// IMU accelerometer data (CAN-native, 8 bytes)
struct ImuAccelMsg {
    int16_t ax;  // mg
    int16_t ay;  // mg
    int16_t az;  // mg
    uint16_t timestamp;  // ms
};
static_assert(sizeof(ImuAccelMsg) == 8, "ImuAccelMsg size mismatch");

// IMU gyroscope data (CAN-native, 8 bytes)
struct ImuGyroMsg {
    int16_t gx;  // mdps
    int16_t gy;  // mdps
    int16_t gz;  // mdps
    uint16_t timestamp;  // ms
};
static_assert(sizeof(ImuGyroMsg) == 8, "ImuGyroMsg size mismatch");

// Node status (CAN-native, 8 bytes)
struct StatusMsg {
    uint8_t state;
    uint8_t flags;
    uint16_t voltage_mv;
    uint16_t temp_c10;  // C
    uint16_t seq;
};
static_assert(sizeof(StatusMsg) == 8, "StatusMsg size mismatch");

#pragma pack(pop)

} // namespace can
