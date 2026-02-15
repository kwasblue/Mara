# robot_host/transport/mqtt/transport.py
"""
MQTT transport for ESP32 communication.

Allows AsyncRobotClient to communicate with ESP32 nodes over MQTT.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import aiomqtt

from robot_host.core import protocol
from robot_host.core.event_bus import EventBus
from robot_host.transport.async_base_transport import AsyncBaseTransport
from .models import (
    MQTTConfig,
    get_cmd_topic,
    get_ack_topic,
    get_telemetry_topic,
)

# Buffer limits to prevent OOM from corrupt/large messages
MAX_RX_BUFFER_SIZE = 65536  # 64KB max

# Exponential backoff parameters
BASE_RECONNECT_DELAY = 1.0  # Start at 1 second
MAX_RECONNECT_DELAY = 30.0  # Cap at 30 seconds


class MQTTTransport(AsyncBaseTransport):
    """
    Async MQTT transport.

    Publishes commands to: mara/{node_id}/cmd
    Subscribes to: mara/{node_id}/ack, mara/{node_id}/telemetry

    Frame format matches the binary protocol used by Serial/TCP transports.

    Key guarantees:
    - start() blocks until connected + subscribed (ready to publish)
    - send_bytes() waits for connection instead of dropping frames
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        node_id: str = "node0",
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        bus: Optional[EventBus] = None,
        use_versioned_topics: bool = False,
    ) -> None:
        super().__init__()
        self._config = MQTTConfig(
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password,
            client_id=client_id or f"host-{node_id}",
        )
        self._node_id = node_id
        self._bus = bus
        self._use_versioned_topics = use_versioned_topics

        # Topics (versioned or legacy based on config)
        self._cmd_topic = get_cmd_topic(node_id, versioned=use_versioned_topics)
        self._ack_topic = get_ack_topic(node_id, versioned=use_versioned_topics)
        self._telemetry_topic = get_telemetry_topic(node_id, versioned=use_versioned_topics)

        # Client state
        self._client: Optional[aiomqtt.Client] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Connection readiness gate (connected + subscribed)
        self._connected_evt = asyncio.Event()
        self._pub_lock = asyncio.Lock()

        # Exponential backoff state
        self._reconnect_attempts = 0
        self._current_delay = BASE_RECONNECT_DELAY

        # RX buffer for frame reassembly (with size limit)
        self._rx_buffer = bytearray()
        self._buffer_overflow_count = 0

    # ------------------------------------------------------------------
    # AsyncBaseTransport Implementation
    # ------------------------------------------------------------------

    async def send_bytes(self, data: bytes) -> None:
        """
        Send already-encoded frame bytes via MQTT.

        Publishes to mara/{node_id}/cmd topic.

        IMPORTANT: waits for connection instead of dropping.
        """
        await self.ensure_connected(timeout_s=5.0)

        if not self._client:
            # Should not happen if connected_evt is set, but be defensive.
            raise RuntimeError("[MQTTTransport] Connected but client is None")

        try:
            async with self._pub_lock:
                await self._client.publish(self._cmd_topic, data, qos=1)
        except Exception as e:
            # Clear readiness so callers will block until reconnect is complete
            self._connected_evt.clear()
            self._publish_event("transport.publish_error", {"error": str(e)})
            raise

    async def start(self, timeout_s: float = 5.0) -> None:
        """
        Start MQTT connection and message loop.

        Blocks until connected + subscribed (ready to publish).
        """
        if self._task is not None and not self._task.done():
            await self.ensure_connected(timeout_s=timeout_s)
            return

        self._running = True
        self._connected_evt.clear()
        self._task = asyncio.create_task(self._run())

        await self.ensure_connected(timeout_s=timeout_s)

    async def stop(self) -> None:
        """Stop MQTT connection."""
        self._running = False
        self._connected_evt.clear()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._client = None

    # ------------------------------------------------------------------
    # Additional Methods
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Check if connected to broker (connected + subscribed)."""
        return self._connected_evt.is_set()

    @property
    def node_id(self) -> str:
        """Get node ID this transport is configured for."""
        return self._node_id

    async def ensure_connected(self, timeout_s: float = 5.0) -> None:
        """Wait until transport is connected + subscribed."""
        if self._connected_evt.is_set():
            return
        try:
            await asyncio.wait_for(self._connected_evt.wait(), timeout=timeout_s)
        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"[MQTTTransport] Not connected within {timeout_s}s to "
                f"{self._config.broker_host}:{self._config.broker_port}"
            ) from e

    async def send_frame(self, msg_type: int, payload: bytes = b"") -> None:
        """
        Encode and send a frame.

        Convenience method that wraps protocol.encode + send_bytes.
        """
        frame = protocol.encode(msg_type, payload)
        await self.send_bytes(frame)

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _publish_event(self, event: str, data: Optional[dict] = None) -> None:
        """Publish event to EventBus if available."""
        if self._bus:
            payload = {"node_id": self._node_id, **(data or {})}
            self._bus.publish(event, payload)

    async def _run(self) -> None:
        """Main connection/reconnect loop with exponential backoff."""
        while self._running:
            try:
                await self._connect_and_listen()
                # Successful connection - reset backoff
                self._reconnect_attempts = 0
                self._current_delay = BASE_RECONNECT_DELAY
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._reconnect_attempts += 1
                self._connected_evt.clear()
                self._client = None

                # Publish error event
                self._publish_event("transport.error", {
                    "error": str(e),
                    "attempt": self._reconnect_attempts,
                })

            if self._running:
                # Exponential backoff: 1s, 2s, 4s, 8s, ... up to 30s
                self._current_delay = min(
                    BASE_RECONNECT_DELAY * (2 ** (self._reconnect_attempts - 1)),
                    MAX_RECONNECT_DELAY
                )
                print(f"[MQTTTransport] Reconnecting in {self._current_delay:.1f}s (attempt {self._reconnect_attempts})...")
                await asyncio.sleep(self._current_delay)

    async def _connect_and_listen(self) -> None:
        """Connect to broker and process messages."""
        print(f"[MQTTTransport] Connecting to {self._config.broker_host}:{self._config.broker_port}...")

        async with aiomqtt.Client(
            hostname=self._config.broker_host,
            port=self._config.broker_port,
            username=self._config.username,
            password=self._config.password,
            identifier=self._config.client_id,
            clean_session=self._config.clean_session,
            keepalive=self._config.keepalive,
        ) as client:
            self._client = client

            # Subscribe first; only then signal readiness
            await client.subscribe(self._ack_topic, qos=1)
            await client.subscribe(self._telemetry_topic, qos=1)

            # Clear buffer on connect
            self._rx_buffer.clear()

            # Now we are truly ready for send_bytes()
            self._connected_evt.set()

            print(f"[MQTTTransport] Connected, subscribing to {self._node_id} topics...")
            print(f"[MQTTTransport] Subscribed to {self._ack_topic}, {self._telemetry_topic}")

            # Publish connected event
            self._publish_event("transport.connected", {
                "broker": self._config.broker_host,
                "port": self._config.broker_port,
            })

            # Process incoming messages
            async for message in client.messages:
                if not self._running:
                    break
                self._on_message(message)

        # Disconnected
        self._connected_evt.clear()
        self._client = None
        self._publish_event("transport.disconnected")

    def _on_message(self, message: aiomqtt.Message) -> None:
        """Handle incoming MQTT message."""
        payload = message.payload
        if not isinstance(payload, (bytes, bytearray)):
            payload = bytes(payload) if payload else b""

        # Check buffer size limit to prevent OOM
        if len(self._rx_buffer) + len(payload) > MAX_RX_BUFFER_SIZE:
            self._buffer_overflow_count += 1
            self._publish_event("transport.buffer_overflow", {
                "buffer_size": len(self._rx_buffer),
                "payload_size": len(payload),
                "overflow_count": self._buffer_overflow_count,
            })
            # Clear buffer and continue - data is likely corrupt anyway
            self._rx_buffer.clear()

        # Accumulate in buffer and extract frames
        self._rx_buffer.extend(payload)
        protocol.extract_frames(self._rx_buffer, self._frame_handler)
