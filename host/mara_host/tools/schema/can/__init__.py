# schema/can/__init__.py
"""
CAN bus message definitions with auto-discovery.

CAN messages are 8-byte frames for hybrid real-time/protocol transport.

Message ID Allocation (11-bit standard IDs):
    0x000-0x0FF: Real-time control (highest priority)
    0x100-0x1FF: Sensor feedback
    0x200-0x2FF: Status/telemetry
    0x300-0x3FF: Protocol transport (JSON wrapping)
    0x400-0x4FF: Configuration/debug

To add a new CAN message:
    1. Create _mymessage.py with a MESSAGE export
    2. Run: mara generate all
"""

from __future__ import annotations

from typing import Any, Dict

from ..discovery import DiscoveryConfig, discover_defs
from .core import CanMessageDef, CanFieldDef, TYPE_INFO


# CAN configuration constants
CAN_CONFIG: Dict[str, Any] = {
    "max_node_id": 15,
    "broadcast_id": 0x0F,
    "default_baud_rate": 500000,
    "proto_payload_size": 6,  # Bytes per frame after header
    "proto_max_frames": 16,
    "proto_max_msg_size": 96,  # 6 * 16
}

# CAN message ID allocation
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


# Auto-discover CAN message definitions
_config = DiscoveryConfig(
    export_name="MESSAGE",
    expected_type=CanMessageDef,
    key_attr="name",
    unique_attrs=("name",),
    on_import_error="error",
)

CAN_MESSAGE_DEFS = discover_defs(__file__, __name__, _config)


def _build_legacy_dict() -> dict[str, dict[str, Any]]:
    """Build legacy CAN_MESSAGES dict."""
    return {name: msg.to_legacy_dict() for name, msg in CAN_MESSAGE_DEFS.items()}


# Legacy export for backward compatibility
CAN_MESSAGES: dict[str, dict[str, Any]] = _build_legacy_dict()


__all__ = [
    "CAN_CONFIG",
    "CAN_MESSAGE_IDS",
    "CAN_MESSAGE_DEFS",
    "CAN_MESSAGES",
    "CAN_NODE_STATES",
    "CanMessageDef",
    "CanFieldDef",
    "TYPE_INFO",
]
