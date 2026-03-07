from enum import IntEnum
import protocol

class MsgType(IntEnum):
    HEARTBEAT = protocol.MSG_HEARTBEAT
    PING      = protocol.MSG_PING
    PONG      = protocol.MSG_PONG
    WHOAMI    = protocol.MSG_WHOAMI
    CMD_JSON  = protocol.MSG_CMD_JSON
    TELEMETRY_BIN = protocol.MSG_TELEMETRY_BIN