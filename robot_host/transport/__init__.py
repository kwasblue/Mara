# robot_host/transport/__init__.py
"""
Transport layer for robot communication.

Available transports:
    - SerialTransport: USB/UART serial communication
    - BluetoothTransport: Bluetooth Classic SPP
    - AsyncTcpTransport: Async WiFi/TCP
    - MQTTTransport: MQTT pub/sub for multi-node
    - CANTransport: CAN bus with hybrid native/protocol support
"""

from robot_host.transport.base_transport import BaseTransport
from robot_host.transport.async_base_transport import AsyncBaseTransport
from robot_host.transport.stream_transport import StreamTransport
from robot_host.transport.serial_transport import SerialTransport
from robot_host.transport.bluetooth_transport import BluetoothTransport
from robot_host.transport.tcp_transport import AsyncTcpTransport

# CAN transport (optional, requires python-can)
try:
    from robot_host.transport.can_transport import CANTransport, VirtualCANTransport
    from robot_host.transport.can_defs import (
        MsgId,
        NodeState,
        SetVelMsg,
        SetSignalMsg,
        HeartbeatMsg,
        EncoderMsg,
        ImuAccelMsg,
        ImuGyroMsg,
        StatusMsg,
    )
    HAS_CAN = True
except ImportError:
    HAS_CAN = False
    CANTransport = None  # type: ignore
    VirtualCANTransport = None  # type: ignore

__all__ = [
    # Base classes
    "BaseTransport",
    "AsyncBaseTransport",
    "StreamTransport",
    # Transports
    "SerialTransport",
    "BluetoothTransport",
    "AsyncTcpTransport",
    # CAN (optional)
    "CANTransport",
    "VirtualCANTransport",
    "HAS_CAN",
    # CAN types (when available)
    "MsgId",
    "NodeState",
    "SetVelMsg",
    "SetSignalMsg",
    "HeartbeatMsg",
    "EncoderMsg",
    "ImuAccelMsg",
    "ImuGyroMsg",
    "StatusMsg",
]
