# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from CAN_MESSAGES in schema.py
#
# This file validates that can_defs.py matches the schema.
# Import can_defs.py directly for runtime use.

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple

# Configuration
MAX_NODE_ID = 15
BROADCAST_ID = 0x0F
DEFAULT_BAUD_RATE = 500000
PROTO_PAYLOAD_SIZE = 6
PROTO_MAX_FRAMES = 16
PROTO_MAX_MSG_SIZE = 96

# Message IDs
class MsgId:
    ESTOP = 0x000
    SYNC = 0x001
    HEARTBEAT_BASE = 0x010
    SET_VEL_BASE = 0x020
    SET_SIGNAL_BASE = 0x030
    STOP_BASE = 0x040
    ARM_BASE = 0x050
    DISARM_BASE = 0x060
    ENCODER_BASE = 0x100
    IMU_ACCEL_BASE = 0x110
    IMU_GYRO_BASE = 0x120
    ANALOG_BASE = 0x130
    STATUS_BASE = 0x200
    ERROR_BASE = 0x210
    TELEM_BASE = 0x220
    PROTO_CMD_BASE = 0x300
    PROTO_RSP_BASE = 0x310
    PROTO_ACK_BASE = 0x320
    CONFIG_BASE = 0x400
    IDENTIFY_BASE = 0x410

# Node state enum
class NodeState(IntEnum):
    INIT = 0
    IDLE = 1
    ARMED = 2
    ACTIVE = 3
    ERROR = 4
    ESTOPPED = 5
    RECOVERING = 6

# Set velocity command (CAN-native, 8 bytes)
@dataclass
class SetVelMsg:
    vx_mm_s: int
    omega_mrad_s: int
    flags: int
    seq: int
    STRUCT_FMT = "<hhHH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.vx_mm_s, self.omega_mrad_s, self.flags, self.seq)

    @classmethod
    def unpack(cls, data: bytes) -> "SetVelMsg":
        vx_mm_s, omega_mrad_s, flags, seq = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(vx_mm_s, omega_mrad_s, flags, seq)


# Set signal value (CAN-native, 8 bytes)
@dataclass
class SetSignalMsg:
    signal_id: int
    value: float
    reserved: int
    STRUCT_FMT = "<HfH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.signal_id, self.value, self.reserved)

    @classmethod
    def unpack(cls, data: bytes) -> "SetSignalMsg":
        signal_id, value, reserved = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(signal_id, value, reserved)


# Node heartbeat (CAN-native, 8 bytes)
@dataclass
class HeartbeatMsg:
    uptime_ms: int
    state: int
    load_pct: int
    errors: int
    STRUCT_FMT = "<IBBH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.uptime_ms, self.state, self.load_pct, self.errors)

    @classmethod
    def unpack(cls, data: bytes) -> "HeartbeatMsg":
        uptime_ms, state, load_pct, errors = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(uptime_ms, state, load_pct, errors)


# Encoder counts and velocity (CAN-native, 8 bytes)
@dataclass
class EncoderMsg:
    counts: int
    velocity: int
    timestamp: int
    STRUCT_FMT = "<ihH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.counts, self.velocity, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "EncoderMsg":
        counts, velocity, timestamp = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(counts, velocity, timestamp)


# IMU accelerometer data (CAN-native, 8 bytes)
@dataclass
class ImuAccelMsg:
    ax: int
    ay: int
    az: int
    timestamp: int
    STRUCT_FMT = "<hhhH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.ax, self.ay, self.az, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "ImuAccelMsg":
        ax, ay, az, timestamp = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(ax, ay, az, timestamp)


# IMU gyroscope data (CAN-native, 8 bytes)
@dataclass
class ImuGyroMsg:
    gx: int
    gy: int
    gz: int
    timestamp: int
    STRUCT_FMT = "<hhhH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.gx, self.gy, self.gz, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> "ImuGyroMsg":
        gx, gy, gz, timestamp = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(gx, gy, gz, timestamp)


# Node status (CAN-native, 8 bytes)
@dataclass
class StatusMsg:
    state: int
    flags: int
    voltage_mv: int
    temp_c10: int
    seq: int
    STRUCT_FMT = "<BBHHH"

    def pack(self) -> bytes:
        return struct.pack(self.STRUCT_FMT, self.state, self.flags, self.voltage_mv, self.temp_c10, self.seq)

    @classmethod
    def unpack(cls, data: bytes) -> "StatusMsg":
        state, flags, voltage_mv, temp_c10, seq = struct.unpack(cls.STRUCT_FMT, data[:struct.calcsize(cls.STRUCT_FMT)])
        return cls(state, flags, voltage_mv, temp_c10, seq)

