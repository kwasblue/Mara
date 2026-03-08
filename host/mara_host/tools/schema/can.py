# schema/can.py
"""CAN bus message definitions for hybrid real-time/protocol transport."""

from typing import Dict, Any

# CAN message IDs and structure definitions.
# Maps to MCU's config/CanDefs.h for interoperability.
#
# Message ID Allocation (11-bit standard IDs):
#   0x000-0x0FF: Real-time control (highest priority)
#   0x100-0x1FF: Sensor feedback
#   0x200-0x2FF: Status/telemetry
#   0x300-0x3FF: Protocol transport (JSON wrapping)
#   0x400-0x4FF: Configuration/debug

CAN_CONFIG: Dict[str, Any] = {
    "max_node_id": 15,
    "broadcast_id": 0x0F,
    "default_baud_rate": 500000,
    "proto_payload_size": 6,  # Bytes per frame after header
    "proto_max_frames": 16,
    "proto_max_msg_size": 96,  # 6 * 16
}

CAN_MESSAGE_IDS: Dict[str, int] = {
    # Real-time Control (0x000-0x0FF) - Highest priority
    "ESTOP": 0x000,           # Emergency stop (broadcast)
    "SYNC": 0x001,            # Sync pulse (broadcast)
    "HEARTBEAT_BASE": 0x010,  # + node_id
    "SET_VEL_BASE": 0x020,    # + node_id
    "SET_SIGNAL_BASE": 0x030, # + node_id
    "STOP_BASE": 0x040,       # + node_id
    "ARM_BASE": 0x050,        # + node_id
    "DISARM_BASE": 0x060,     # + node_id

    # Sensor Feedback (0x100-0x1FF)
    "ENCODER_BASE": 0x100,    # + node_id
    "IMU_ACCEL_BASE": 0x110,  # + node_id
    "IMU_GYRO_BASE": 0x120,   # + node_id
    "ANALOG_BASE": 0x130,     # + node_id

    # Status/Telemetry (0x200-0x2FF)
    "STATUS_BASE": 0x200,     # + node_id
    "ERROR_BASE": 0x210,      # + node_id
    "TELEM_BASE": 0x220,      # + node_id

    # Protocol Transport (0x300-0x3FF)
    "PROTO_CMD_BASE": 0x300,  # + node_id
    "PROTO_RSP_BASE": 0x310,  # + node_id
    "PROTO_ACK_BASE": 0x320,  # + node_id

    # Configuration (0x400-0x4FF)
    "CONFIG_BASE": 0x400,     # + node_id
    "IDENTIFY_BASE": 0x410,   # + node_id
}

CAN_MESSAGES: Dict[str, Dict[str, Any]] = {
    # --- Real-time Control Messages ---
    "SET_VEL": {
        "base_id": "SET_VEL_BASE",
        "direction": "host->mcu",
        "description": "Set velocity command (CAN-native, 8 bytes)",
        "struct": [
            {"name": "vx_mm_s", "type": "i16", "scale": 1000.0, "unit": "m/s"},
            {"name": "omega_mrad_s", "type": "i16", "scale": 1000.0, "unit": "rad/s"},
            {"name": "flags", "type": "u16"},
            {"name": "seq", "type": "u16"},
        ],
    },
    "SET_SIGNAL": {
        "base_id": "SET_SIGNAL_BASE",
        "direction": "host->mcu",
        "description": "Set signal value (CAN-native, 8 bytes)",
        "struct": [
            {"name": "signal_id", "type": "u16"},
            {"name": "value", "type": "f32"},
            {"name": "reserved", "type": "u16"},
        ],
    },
    "HEARTBEAT": {
        "base_id": "HEARTBEAT_BASE",
        "direction": "both",
        "description": "Node heartbeat (CAN-native, 8 bytes)",
        "struct": [
            {"name": "uptime_ms", "type": "u32"},
            {"name": "state", "type": "u8"},
            {"name": "load_pct", "type": "u8"},
            {"name": "errors", "type": "u16"},
        ],
    },

    # --- Sensor Feedback Messages ---
    "ENCODER": {
        "base_id": "ENCODER_BASE",
        "direction": "mcu->host",
        "description": "Encoder counts and velocity (CAN-native, 8 bytes)",
        "struct": [
            {"name": "counts", "type": "i32"},
            {"name": "velocity", "type": "i16", "unit": "counts/s"},
            {"name": "timestamp", "type": "u16", "unit": "ms"},
        ],
    },
    "IMU_ACCEL": {
        "base_id": "IMU_ACCEL_BASE",
        "direction": "mcu->host",
        "description": "IMU accelerometer data (CAN-native, 8 bytes)",
        "struct": [
            {"name": "ax", "type": "i16", "unit": "mg"},
            {"name": "ay", "type": "i16", "unit": "mg"},
            {"name": "az", "type": "i16", "unit": "mg"},
            {"name": "timestamp", "type": "u16", "unit": "ms"},
        ],
    },
    "IMU_GYRO": {
        "base_id": "IMU_GYRO_BASE",
        "direction": "mcu->host",
        "description": "IMU gyroscope data (CAN-native, 8 bytes)",
        "struct": [
            {"name": "gx", "type": "i16", "unit": "mdps"},
            {"name": "gy", "type": "i16", "unit": "mdps"},
            {"name": "gz", "type": "i16", "unit": "mdps"},
            {"name": "timestamp", "type": "u16", "unit": "ms"},
        ],
    },

    # --- Status Messages ---
    "STATUS": {
        "base_id": "STATUS_BASE",
        "direction": "mcu->host",
        "description": "Node status (CAN-native, 8 bytes)",
        "struct": [
            {"name": "state", "type": "u8"},
            {"name": "flags", "type": "u8"},  # Bitfield: armed, active, estopped, error
            {"name": "voltage_mv", "type": "u16"},
            {"name": "temp_c10", "type": "u16", "scale": 10.0, "unit": "C"},
            {"name": "seq", "type": "u16"},
        ],
    },
}

# Node state enum (matches MCU can::NodeState)
CAN_NODE_STATES: Dict[str, int] = {
    "INIT": 0,
    "IDLE": 1,
    "ARMED": 2,
    "ACTIVE": 3,
    "ERROR": 4,
    "ESTOPPED": 5,
    "RECOVERING": 6,
}
