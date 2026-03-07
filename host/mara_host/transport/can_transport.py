# mara_host/transport/can_transport.py
"""
CAN bus transport with hybrid native/protocol support.

This transport provides communication with MCU nodes over CAN bus using
the python-can library. It supports multiple backends:
    - Linux: SocketCAN (can0, vcan0, etc.)
    - Windows: PCAN, Vector, Kvaser
    - macOS: PCAN USB adapters

Hybrid approach:
    - CAN-native messages: Compact 8-byte packed structures for real-time
      control (velocity, signals, encoder feedback, IMU data)
    - Protocol transport: Multi-frame transport for JSON commands using
      the standard framing protocol

Usage:
    transport = CANTransport(channel="can0", node_id=0)
    await transport.start()

    # Send velocity command (CAN-native)
    await transport.send_velocity(0.5, 0.1)

    # Send JSON command (protocol wrapped)
    await transport.send_bytes(protocol_frame)

    await transport.stop()

Requirements:
    pip install python-can>=4.0.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any

from mara_host.transport.async_base_transport import AsyncBaseTransport
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
    ProtoReassembler,
    make_id,
    extract_node_id,
    get_base_id,
    encode_protocol_frames,
    PROTO_PAYLOAD_SIZE,
    DEFAULT_BAUD_RATE,
    BROADCAST_ID,
)

try:
    import can
    from can import Bus, Message
    HAS_CAN = True
except ImportError:
    HAS_CAN = False
    can = None  # type: ignore
    Bus = None  # type: ignore
    Message = None  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# CALLBACK TYPES
# =============================================================================

VelocityCallback = Callable[[float, float, int], None]  # vx, omega, seq
SignalCallback = Callable[[int, float], None]           # signal_id, value
HeartbeatCallback = Callable[[int, int, NodeState], None]  # node_id, uptime, state
EncoderCallback = Callable[[int, int, int], None]       # node_id, counts, velocity
ImuAccelCallback = Callable[[int, float, float, float], None]  # node_id, ax, ay, az
ImuGyroCallback = Callable[[int, float, float, float], None]   # node_id, gx, gy, gz
StatusCallback = Callable[[int, StatusMsg], None]       # node_id, status


# =============================================================================
# CAN TRANSPORT STATISTICS
# =============================================================================

@dataclass
class CANStats:
    """CAN transport statistics."""
    tx_count: int = 0
    rx_count: int = 0
    tx_errors: int = 0
    rx_errors: int = 0
    proto_tx_count: int = 0
    proto_rx_count: int = 0
    native_tx_count: int = 0
    native_rx_count: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def uptime_s(self) -> float:
        return time.time() - self.start_time


# =============================================================================
# CAN TRANSPORT
# =============================================================================

class CANTransport(AsyncBaseTransport):
    """
    Async CAN bus transport with hybrid native/protocol support.

    Features:
        - CAN-native message dispatch for real-time control
        - Multi-frame protocol transport for JSON commands
        - Automatic frame reassembly for incoming protocol messages
        - Multiple CAN backend support via python-can
        - Configurable node addressing

    Args:
        channel: CAN interface name (e.g., "can0", "vcan0", "PCAN_USBBUS1")
        bustype: CAN backend type (e.g., "socketcan", "pcan", "vector")
        bitrate: CAN bus bitrate (default 500000)
        node_id: Local node ID (0-14, 15 = broadcast)
        interface_kwargs: Additional kwargs passed to can.Bus()
    """

    def __init__(
        self,
        channel: str = "can0",
        bustype: str = "socketcan",
        bitrate: int = DEFAULT_BAUD_RATE,
        node_id: int = 0,
        **interface_kwargs: Any,
    ):
        super().__init__()

        if not HAS_CAN:
            raise ImportError(
                "python-can is required for CAN transport. "
                "Install with: pip install python-can>=4.0.0"
            )

        self._channel = channel
        self._bustype = bustype
        self._bitrate = bitrate
        self._node_id = node_id
        self._interface_kwargs = interface_kwargs

        self._bus: Optional[Bus] = None
        self._running = False
        self._read_task: Optional[asyncio.Task] = None
        self._stats = CANStats()

        # Protocol reassembly
        self._proto_reassembler = ProtoReassembler()
        self._proto_tx_msg_id = 0

        # Native message callbacks
        self._on_velocity: Optional[VelocityCallback] = None
        self._on_signal: Optional[SignalCallback] = None
        self._on_heartbeat: Optional[HeartbeatCallback] = None
        self._on_encoder: Optional[EncoderCallback] = None
        self._on_imu_accel: Optional[ImuAccelCallback] = None
        self._on_imu_gyro: Optional[ImuGyroCallback] = None
        self._on_status: Optional[StatusCallback] = None

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def is_connected(self) -> bool:
        return self._bus is not None and self._running

    @property
    def node_id(self) -> int:
        return self._node_id

    @node_id.setter
    def node_id(self, value: int) -> None:
        if not 0 <= value <= 15:
            raise ValueError("node_id must be 0-15")
        self._node_id = value

    @property
    def stats(self) -> CANStats:
        return self._stats

    # =========================================================================
    # CALLBACK REGISTRATION
    # =========================================================================

    def set_velocity_callback(self, callback: Optional[VelocityCallback]) -> None:
        """Set callback for incoming velocity messages."""
        self._on_velocity = callback

    def set_signal_callback(self, callback: Optional[SignalCallback]) -> None:
        """Set callback for incoming signal messages."""
        self._on_signal = callback

    def set_heartbeat_callback(self, callback: Optional[HeartbeatCallback]) -> None:
        """Set callback for incoming heartbeat messages."""
        self._on_heartbeat = callback

    def set_encoder_callback(self, callback: Optional[EncoderCallback]) -> None:
        """Set callback for incoming encoder messages."""
        self._on_encoder = callback

    def set_imu_accel_callback(self, callback: Optional[ImuAccelCallback]) -> None:
        """Set callback for incoming IMU accelerometer messages."""
        self._on_imu_accel = callback

    def set_imu_gyro_callback(self, callback: Optional[ImuGyroCallback]) -> None:
        """Set callback for incoming IMU gyroscope messages."""
        self._on_imu_gyro = callback

    def set_status_callback(self, callback: Optional[StatusCallback]) -> None:
        """Set callback for incoming status messages."""
        self._on_status = callback

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self) -> None:
        """Start the CAN transport."""
        if self._running:
            return

        try:
            self._bus = can.Bus(
                channel=self._channel,
                bustype=self._bustype,
                bitrate=self._bitrate,
                **self._interface_kwargs,
            )
            self._running = True
            self._stats = CANStats()

            # Start background read task
            self._read_task = asyncio.create_task(self._read_loop())

            logger.info(
                "CAN transport started: %s (%s) @ %d bps, node %d",
                self._channel, self._bustype, self._bitrate, self._node_id
            )

        except Exception as e:
            logger.error("Failed to start CAN transport: %s", e)
            self._running = False
            raise

    async def stop(self) -> None:
        """Stop the CAN transport."""
        if not self._running:
            return

        self._running = False

        # Cancel read task
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        # Close bus
        if self._bus:
            self._bus.shutdown()
            self._bus = None

        logger.info("CAN transport stopped")

    # =========================================================================
    # PROTOCOL TRANSPORT (send_bytes interface)
    # =========================================================================

    async def send_bytes(self, data: bytes) -> None:
        """
        Send data as protocol frames.

        Large messages are fragmented into multiple CAN frames.

        Args:
            data: Protocol frame bytes to send
        """
        if not self.is_connected:
            raise RuntimeError("CAN transport not connected")

        await self.send_protocol(data, target_node=BROADCAST_ID)

    async def send_protocol(
        self,
        data: bytes,
        target_node: int = BROADCAST_ID,
    ) -> bool:
        """
        Send protocol data with multi-frame fragmentation.

        Args:
            data: Data to send (up to 96 bytes)
            target_node: Target node ID (default: broadcast)

        Returns:
            True if all frames sent successfully
        """
        if not self.is_connected:
            return False

        # Get next message ID
        msg_id = self._proto_tx_msg_id
        self._proto_tx_msg_id = (self._proto_tx_msg_id + 1) & 0xFF

        # Fragment into frames
        frames = encode_protocol_frames(data, msg_id)
        can_id = make_id(MsgId.PROTO_CMD_BASE, target_node)

        # Send all frames
        for frame_data in frames:
            if not await self._send_can_frame(can_id, frame_data):
                return False
            self._stats.proto_tx_count += 1

        return True

    # =========================================================================
    # NATIVE MESSAGE SENDING
    # =========================================================================

    async def send_velocity(self, vx: float, omega: float, seq: int = 0) -> bool:
        """Send velocity command (CAN-native)."""
        if not self.is_connected:
            return False

        msg = SetVelMsg.from_floats(vx, omega, seq)
        can_id = make_id(MsgId.SET_VEL_BASE, self._node_id)

        if await self._send_can_frame(can_id, msg.pack()):
            self._stats.native_tx_count += 1
            return True
        return False

    async def send_signal(self, signal_id: int, value: float) -> bool:
        """Send signal value (CAN-native)."""
        if not self.is_connected:
            return False

        msg = SetSignalMsg(signal_id, value)
        can_id = make_id(MsgId.SET_SIGNAL_BASE, self._node_id)

        if await self._send_can_frame(can_id, msg.pack()):
            self._stats.native_tx_count += 1
            return True
        return False

    async def send_heartbeat(
        self,
        uptime_ms: int,
        state: NodeState,
        load_pct: int = 0,
        errors: int = 0,
    ) -> bool:
        """Send heartbeat (CAN-native)."""
        if not self.is_connected:
            return False

        msg = HeartbeatMsg(uptime_ms, state.value, load_pct, errors)
        can_id = make_id(MsgId.HEARTBEAT_BASE, self._node_id)

        if await self._send_can_frame(can_id, msg.pack()):
            self._stats.native_tx_count += 1
            return True
        return False

    async def send_estop(self) -> bool:
        """Send emergency stop (broadcast, highest priority)."""
        if not self.is_connected:
            return False

        # E-stop is broadcast, no payload
        return await self._send_can_frame(MsgId.ESTOP, b"")

    async def send_stop(self, target_node: int = BROADCAST_ID) -> bool:
        """Send stop command to specific node."""
        if not self.is_connected:
            return False

        can_id = make_id(MsgId.STOP_BASE, target_node)
        return await self._send_can_frame(can_id, b"")

    # =========================================================================
    # PRIVATE METHODS
    # =========================================================================

    async def _send_can_frame(self, can_id: int, data: bytes) -> bool:
        """Send a single CAN frame."""
        if not self._bus:
            return False

        try:
            msg = Message(
                arbitration_id=can_id,
                data=data[:8],  # CAN 2.0 max 8 bytes
                is_extended_id=False,
            )

            # Use thread pool for blocking send
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._bus.send, msg)

            self._stats.tx_count += 1
            return True

        except Exception as e:
            logger.warning("CAN send error: %s", e)
            self._stats.tx_errors += 1
            return False

    async def _read_loop(self) -> None:
        """Background task to read CAN messages."""
        loop = asyncio.get_event_loop()

        while self._running and self._bus:
            try:
                # Non-blocking receive with timeout
                msg = await loop.run_in_executor(
                    None,
                    lambda: self._bus.recv(timeout=0.1) if self._bus else None
                )

                if msg:
                    self._stats.rx_count += 1
                    self._process_message(msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("CAN read error: %s", e)
                self._stats.rx_errors += 1
                await asyncio.sleep(0.01)

    def _process_message(self, msg: Message) -> None:
        """Process a received CAN message."""
        can_id = msg.arbitration_id
        data = bytes(msg.data)
        node_id = extract_node_id(can_id)
        base_id = get_base_id(can_id)

        # Check for protocol frames
        if base_id in (MsgId.PROTO_CMD_BASE, MsgId.PROTO_RSP_BASE):
            self._handle_protocol_frame(node_id, data)
            return

        # Handle native messages
        self._handle_native_message(base_id, node_id, data)

    def _handle_protocol_frame(self, node_id: int, data: bytes) -> None:
        """Handle incoming protocol frame."""
        timestamp_ms = int(time.time() * 1000)
        complete_msg = self._proto_reassembler.add_frame(node_id, data, timestamp_ms)

        if complete_msg:
            self._stats.proto_rx_count += 1
            # Dispatch to standard frame handler
            self._handle_frame(complete_msg)

    def _handle_native_message(self, base_id: int, node_id: int, data: bytes) -> None:
        """Handle native CAN message."""
        self._stats.native_rx_count += 1

        try:
            if base_id == MsgId.ESTOP:
                logger.warning("E-STOP received!")
                # Could trigger a callback here

            elif base_id == MsgId.SET_VEL_BASE and self._on_velocity:
                msg = SetVelMsg.unpack(data)
                vx, omega = msg.to_floats()
                self._on_velocity(vx, omega, msg.seq)

            elif base_id == MsgId.SET_SIGNAL_BASE and self._on_signal:
                msg = SetSignalMsg.unpack(data)
                self._on_signal(msg.signal_id, msg.value)

            elif base_id == MsgId.HEARTBEAT_BASE and self._on_heartbeat:
                msg = HeartbeatMsg.unpack(data)
                self._on_heartbeat(node_id, msg.uptime_ms, msg.node_state)

            elif base_id == MsgId.ENCODER_BASE and self._on_encoder:
                msg = EncoderMsg.unpack(data)
                self._on_encoder(node_id, msg.counts, msg.velocity)

            elif base_id == MsgId.IMU_ACCEL_BASE and self._on_imu_accel:
                msg = ImuAccelMsg.unpack(data)
                ax, ay, az = msg.to_g()
                self._on_imu_accel(node_id, ax, ay, az)

            elif base_id == MsgId.IMU_GYRO_BASE and self._on_imu_gyro:
                msg = ImuGyroMsg.unpack(data)
                gx, gy, gz = msg.to_dps()
                self._on_imu_gyro(node_id, gx, gy, gz)

            elif base_id == MsgId.STATUS_BASE and self._on_status:
                msg = StatusMsg.unpack(data)
                self._on_status(node_id, msg)

        except Exception as e:
            logger.warning("Error processing native message 0x%03X: %s", base_id, e)


# =============================================================================
# VIRTUAL CAN TRANSPORT (for testing)
# =============================================================================

class VirtualCANTransport(CANTransport):
    """
    Virtual CAN transport for testing without hardware.

    Uses python-can's virtual bus for loopback testing.
    """

    def __init__(self, channel: str = "vcan0", node_id: int = 0, **kwargs: Any):
        super().__init__(
            channel=channel,
            bustype="virtual",
            node_id=node_id,
            **kwargs,
        )
