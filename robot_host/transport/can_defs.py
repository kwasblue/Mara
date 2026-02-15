# robot_host/transport/can_defs.py
"""
CAN bus message definitions for hybrid real-time/protocol transport.

This module mirrors the MCU's config/CanDefs.h for interoperability.
All message structures use little-endian byte order.

Message ID Allocation (11-bit standard IDs):
    0x000-0x0FF: Real-time control (highest priority)
    0x100-0x1FF: Sensor feedback
    0x200-0x2FF: Status/telemetry
    0x300-0x3FF: Protocol transport (JSON wrapping)
    0x400-0x4FF: Configuration/debug
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple, Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_NODE_ID = 15
BROADCAST_ID = 0x0F
DEFAULT_BAUD_RATE = 500000

# Protocol transport constants
PROTO_PAYLOAD_SIZE = 6   # Bytes per frame after header
PROTO_MAX_FRAMES = 16    # Max frames per message
PROTO_MAX_MSG_SIZE = PROTO_PAYLOAD_SIZE * PROTO_MAX_FRAMES  # 96 bytes


# =============================================================================
# MESSAGE IDS
# =============================================================================

class MsgId:
    """CAN message ID base addresses."""
    # Real-time Control (0x000-0x0FF) - Highest priority
    ESTOP = 0x000            # Emergency stop (broadcast)
    SYNC = 0x001             # Sync pulse (broadcast)
    HEARTBEAT_BASE = 0x010   # + node_id
    SET_VEL_BASE = 0x020     # + node_id
    SET_SIGNAL_BASE = 0x030  # + node_id
    STOP_BASE = 0x040        # + node_id
    ARM_BASE = 0x050         # + node_id
    DISARM_BASE = 0x060      # + node_id

    # Sensor Feedback (0x100-0x1FF)
    ENCODER_BASE = 0x100     # + node_id
    IMU_ACCEL_BASE = 0x110   # + node_id
    IMU_GYRO_BASE = 0x120    # + node_id
    ANALOG_BASE = 0x130      # + node_id

    # Status/Telemetry (0x200-0x2FF)
    STATUS_BASE = 0x200      # + node_id
    ERROR_BASE = 0x210       # + node_id
    TELEM_BASE = 0x220       # + node_id

    # Protocol Transport (0x300-0x3FF)
    PROTO_CMD_BASE = 0x300   # + node_id
    PROTO_RSP_BASE = 0x310   # + node_id
    PROTO_ACK_BASE = 0x320   # + node_id

    # Configuration (0x400-0x4FF)
    CONFIG_BASE = 0x400      # + node_id
    IDENTIFY_BASE = 0x410    # + node_id


def make_id(base: int, node_id: int) -> int:
    """Build message ID with node address."""
    return base | (node_id & 0x0F)


def extract_node_id(msg_id: int) -> int:
    """Extract node ID from message ID."""
    return msg_id & 0x0F


def get_base_id(msg_id: int) -> int:
    """Extract base ID (without node bits) from message ID."""
    return msg_id & 0xFF0


# =============================================================================
# NODE STATE ENUM
# =============================================================================

class NodeState(IntEnum):
    """Node state enum (matches MCU can::NodeState)."""
    INIT = 0
    IDLE = 1
    ARMED = 2
    ACTIVE = 3
    ERROR = 4
    ESTOPPED = 5
    RECOVERING = 6


# =============================================================================
# MESSAGE STRUCTURES
# =============================================================================

@dataclass
class SetVelMsg:
    """Velocity command message (8 bytes)."""
    vx_mm_s: int       # Linear velocity in mm/s (±32767)
    omega_mrad_s: int  # Angular velocity in mrad/s (±32767)
    flags: int = 0     # Reserved flags
    seq: int = 0       # Sequence number

    VX_SCALE = 1000.0     # mm/s
    OMEGA_SCALE = 1000.0  # mrad/s
    STRUCT_FMT = "<hhHH"  # Little-endian: 2x int16, 2x uint16

    @classmethod
    def from_floats(cls, vx: float, omega: float, seq: int = 0) -> "SetVelMsg":
        """Create from float velocities."""
        return cls(
            vx_mm_s=int(vx * cls.VX_SCALE),
            omega_mrad_s=int(omega * cls.OMEGA_SCALE),
            flags=0,
            seq=seq,
        )

    def to_floats(self) -> Tuple[float, float]:
        """Convert to float velocities (vx, omega)."""
        return (
            self.vx_mm_s / self.VX_SCALE,
            self.omega_mrad_s / self.OMEGA_SCALE,
        )

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(
            self.STRUCT_FMT,
            self.vx_mm_s,
            self.omega_mrad_s,
            self.flags,
            self.seq,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "SetVelMsg":
        """Unpack from 8 bytes."""
        vx, omega, flags, seq = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(vx, omega, flags, seq)


@dataclass
class SetSignalMsg:
    """Signal value message (8 bytes)."""
    signal_id: int   # Signal bus ID
    value: float     # Signal value (IEEE 754)
    reserved: int = 0

    STRUCT_FMT = "<HfH"  # Little-endian: uint16, float32, uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(self.STRUCT_FMT, self.signal_id, self.value, self.reserved)

    @classmethod
    def unpack(cls, data: bytes) -> "SetSignalMsg":
        """Unpack from 8 bytes."""
        sig_id, value, reserved = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(sig_id, value, reserved)


@dataclass
class HeartbeatMsg:
    """Heartbeat message (8 bytes)."""
    uptime_ms: int    # Uptime in milliseconds
    state: int        # NodeState enum
    load_pct: int     # CPU load percentage
    errors: int       # Error count since boot

    STRUCT_FMT = "<IBBH"  # Little-endian: uint32, uint8, uint8, uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(
            self.STRUCT_FMT,
            self.uptime_ms,
            self.state,
            self.load_pct,
            self.errors,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "HeartbeatMsg":
        """Unpack from 8 bytes."""
        uptime, state, load, errors = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(uptime, state, load, errors)

    @property
    def node_state(self) -> NodeState:
        """Get state as NodeState enum."""
        return NodeState(self.state)


@dataclass
class EncoderMsg:
    """Encoder feedback message (8 bytes)."""
    counts: int       # Encoder counts (signed 32-bit)
    velocity: int     # Counts per second (signed 16-bit)
    timestamp: int    # Local timestamp in ms (wraps at 65535)

    STRUCT_FMT = "<ihH"  # Little-endian: int32, int16, uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(self.STRUCT_FMT, self.counts, self.velocity, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "EncoderMsg":
        """Unpack from 8 bytes."""
        counts, velocity, timestamp = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(counts, velocity, timestamp)


@dataclass
class ImuAccelMsg:
    """IMU accelerometer message (8 bytes)."""
    ax: int           # Accelerometer X in mg (±32767 = ±32g)
    ay: int           # Accelerometer Y
    az: int           # Accelerometer Z
    timestamp: int    # Local timestamp in ms

    STRUCT_FMT = "<hhhH"  # Little-endian: 3x int16, uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(self.STRUCT_FMT, self.ax, self.ay, self.az, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "ImuAccelMsg":
        """Unpack from 8 bytes."""
        ax, ay, az, ts = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(ax, ay, az, ts)

    def to_g(self) -> Tuple[float, float, float]:
        """Convert to g units."""
        return (self.ax / 1000.0, self.ay / 1000.0, self.az / 1000.0)


@dataclass
class ImuGyroMsg:
    """IMU gyroscope message (8 bytes)."""
    gx: int           # Gyroscope X in mdps (±32767 = ±32768 dps)
    gy: int           # Gyroscope Y
    gz: int           # Gyroscope Z
    timestamp: int    # Local timestamp in ms

    STRUCT_FMT = "<hhhH"  # Little-endian: 3x int16, uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(self.STRUCT_FMT, self.gx, self.gy, self.gz, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "ImuGyroMsg":
        """Unpack from 8 bytes."""
        gx, gy, gz, ts = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(gx, gy, gz, ts)

    def to_dps(self) -> Tuple[float, float, float]:
        """Convert to degrees per second."""
        return (self.gx / 1000.0, self.gy / 1000.0, self.gz / 1000.0)


@dataclass
class StatusMsg:
    """Node status message (8 bytes)."""
    state: int        # NodeState enum
    flags: int        # Bitfield: armed(0), active(1), estopped(2), error(3)
    voltage_mv: int   # System voltage in mV
    temp_c10: int     # Temperature in 0.1°C
    seq: int          # Status sequence number

    STRUCT_FMT = "<BBHHH"  # Little-endian: 2x uint8, 3x uint16

    def pack(self) -> bytes:
        """Pack to 8 bytes."""
        return struct.pack(
            self.STRUCT_FMT,
            self.state,
            self.flags,
            self.voltage_mv,
            self.temp_c10,
            self.seq,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "StatusMsg":
        """Unpack from 8 bytes."""
        state, flags, voltage, temp, seq = struct.unpack(cls.STRUCT_FMT, data[:8])
        return cls(state, flags, voltage, temp, seq)

    @property
    def armed(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def active(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def estopped(self) -> bool:
        return bool(self.flags & 0x04)

    @property
    def has_error(self) -> bool:
        return bool(self.flags & 0x08)

    @property
    def voltage_v(self) -> float:
        return self.voltage_mv / 1000.0

    @property
    def temp_c(self) -> float:
        return self.temp_c10 / 10.0


# =============================================================================
# PROTOCOL TRANSPORT (Multi-frame JSON wrapping)
# =============================================================================

@dataclass
class ProtoFrameHeader:
    """Protocol frame header (2 bytes)."""
    frame_id: int      # Frame sequence (0-15)
    total_frames: int  # Total frames in message (1-16)
    msg_id: int        # Message identifier for reassembly

    def pack(self) -> bytes:
        """Pack header to 2 bytes."""
        byte0 = (self.frame_id & 0x0F) | ((self.total_frames & 0x0F) << 4)
        return bytes([byte0, self.msg_id])

    @classmethod
    def unpack(cls, data: bytes) -> "ProtoFrameHeader":
        """Unpack header from 2 bytes."""
        byte0 = data[0]
        frame_id = byte0 & 0x0F
        total_frames = (byte0 >> 4) & 0x0F
        msg_id = data[1]
        return cls(frame_id, total_frames, msg_id)


def encode_protocol_frames(data: bytes, msg_id: int) -> list[bytes]:
    """
    Encode data into protocol transport frames.

    Each frame is 8 bytes:
        - 2 bytes header (frame_id, total_frames, msg_id)
        - 6 bytes payload

    Returns list of 8-byte frames.
    """
    if len(data) > PROTO_MAX_MSG_SIZE:
        raise ValueError(f"Data too large: {len(data)} > {PROTO_MAX_MSG_SIZE}")

    frames = []
    num_frames = (len(data) + PROTO_PAYLOAD_SIZE - 1) // PROTO_PAYLOAD_SIZE
    if num_frames == 0:
        num_frames = 1

    for i in range(num_frames):
        offset = i * PROTO_PAYLOAD_SIZE
        chunk = data[offset:offset + PROTO_PAYLOAD_SIZE]
        # Pad with zeros if needed
        chunk = chunk.ljust(PROTO_PAYLOAD_SIZE, b'\x00')

        header = ProtoFrameHeader(frame_id=i, total_frames=num_frames, msg_id=msg_id)
        frame = header.pack() + chunk
        frames.append(frame)

    return frames


class ProtoReassembler:
    """Reassemble multi-frame protocol messages."""

    def __init__(self, timeout_ms: int = 500):
        self.timeout_ms = timeout_ms
        self._buffers: dict[int, dict] = {}  # node_id -> reassembly state

    def add_frame(
        self,
        node_id: int,
        data: bytes,
        timestamp_ms: int,
    ) -> Optional[bytes]:
        """
        Add a frame and return complete message if ready.

        Returns None if message is incomplete, or the complete message bytes
        when all frames have been received.
        """
        if len(data) < 2:
            return None

        header = ProtoFrameHeader.unpack(data[:2])
        payload = data[2:8]

        # Get or create reassembly buffer
        if node_id not in self._buffers:
            self._buffers[node_id] = {
                "msg_id": header.msg_id,
                "total_frames": header.total_frames,
                "received_mask": 0,
                "data": bytearray(PROTO_MAX_MSG_SIZE),
                "last_time": timestamp_ms,
            }

        buf = self._buffers[node_id]

        # Check for timeout or new message
        if (timestamp_ms - buf["last_time"] > self.timeout_ms or
                buf["msg_id"] != header.msg_id or
                buf["total_frames"] != header.total_frames):
            # Reset buffer for new message
            buf["msg_id"] = header.msg_id
            buf["total_frames"] = header.total_frames
            buf["received_mask"] = 0
            buf["data"] = bytearray(PROTO_MAX_MSG_SIZE)

        buf["last_time"] = timestamp_ms

        # Store frame data
        offset = header.frame_id * PROTO_PAYLOAD_SIZE
        buf["data"][offset:offset + PROTO_PAYLOAD_SIZE] = payload
        buf["received_mask"] |= (1 << header.frame_id)

        # Check if complete
        expected_mask = (1 << header.total_frames) - 1
        if (buf["received_mask"] & expected_mask) == expected_mask:
            # Message complete
            total_len = header.total_frames * PROTO_PAYLOAD_SIZE
            result = bytes(buf["data"][:total_len]).rstrip(b'\x00')
            del self._buffers[node_id]
            return result

        return None

    def clear(self, node_id: Optional[int] = None) -> None:
        """Clear reassembly buffer(s)."""
        if node_id is None:
            self._buffers.clear()
        elif node_id in self._buffers:
            del self._buffers[node_id]


# =============================================================================
# CONVENIENCE ENCODING FUNCTIONS
# =============================================================================

def encode_set_vel(vx: float, omega: float, seq: int = 0) -> bytes:
    """Encode velocity command to 8 bytes."""
    return SetVelMsg.from_floats(vx, omega, seq).pack()


def encode_set_signal(signal_id: int, value: float) -> bytes:
    """Encode signal value to 8 bytes."""
    return SetSignalMsg(signal_id, value).pack()


def encode_heartbeat(uptime_ms: int, state: NodeState, load_pct: int = 0, errors: int = 0) -> bytes:
    """Encode heartbeat to 8 bytes."""
    return HeartbeatMsg(uptime_ms, state.value, load_pct, errors).pack()


def encode_encoder(counts: int, velocity: int, timestamp: int) -> bytes:
    """Encode encoder feedback to 8 bytes."""
    return EncoderMsg(counts, velocity, timestamp).pack()
