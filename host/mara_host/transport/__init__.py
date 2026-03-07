# mara_host/transport/__init__.py
"""
Transport layer for robot communication.

Available transports:
    - SerialTransport: USB/UART serial communication
    - BluetoothSerialTransport: Bluetooth Classic SPP
    - AsyncTcpTransport: Async WiFi/TCP
    - MQTTTransport: MQTT pub/sub for multi-node
    - CANTransport: CAN bus with hybrid native/protocol support
"""

from mara_host.transport.base_transport import BaseTransport
from mara_host.transport.async_base_transport import AsyncBaseTransport
from mara_host.transport.stream_transport import StreamTransport
from mara_host.transport.serial_transport import SerialTransport
from mara_host.transport.bluetooth_transport import BluetoothSerialTransport
from mara_host.transport.tcp_transport import AsyncTcpTransport

# CAN transport (optional, requires python-can)
try:
    from mara_host.transport.can_transport import CANTransport, VirtualCANTransport
    from mara_host.transport.can_defs import (
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
    "BluetoothSerialTransport",
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
