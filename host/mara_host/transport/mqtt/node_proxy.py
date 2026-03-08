# mara_host/mqtt/node_proxy.py
"""
NodeProxy - represents a single node with its transport and client.
"""

from __future__ import annotations

import time
from typing import Optional

from mara_host.core.event_bus import EventBus
from mara_host.command.client import MaraClient
from .transport import MQTTTransport
from .models import NodeInfo, NodeStatus, NodeState


class NodeProxy:
    """
    Represents a single ESP32 node over MQTT.

    Wraps MQTTTransport + MaraClient for a specific node_id.
    Provides convenient access to the client and tracks node status.
    """

    def __init__(
        self,
        node_id: str,
        broker_host: str,
        broker_port: int = 1883,
        bus: Optional[EventBus] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        heartbeat_timeout_s: float = 5.0,
        require_version_match: bool = True,
    ) -> None:
        self._node_id = node_id
        self._bus = bus or EventBus()
        self._heartbeat_timeout_s = heartbeat_timeout_s

        # Create transport for this node (with EventBus for observability)
        self._transport = MQTTTransport(
            broker_host=broker_host,
            broker_port=broker_port,
            node_id=node_id,
            username=username,
            password=password,
            bus=self._bus,
        )

        # Create client using the transport
        # Use longer timeout for MQTT (no continuous telemetry stream)
        self._client = MaraClient(
            transport=self._transport,
            bus=self._bus,
            require_version_match=require_version_match,
            connection_timeout_s=heartbeat_timeout_s,
        )

        # Status tracking
        self._status = NodeStatus(node_id=node_id)
        self._info: Optional[NodeInfo] = None
        self._video_url: Optional[str] = None

        # Subscribe to relevant events
        self._bus.subscribe("heartbeat", self._on_heartbeat)
        self._bus.subscribe("telemetry", self._on_telemetry)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def node_id(self) -> str:
        """Get node ID."""
        return self._node_id

    @property
    def client(self) -> MaraClient:
        """Get the MaraClient for this node."""
        return self._client

    @property
    def transport(self) -> MQTTTransport:
        """Get the underlying MQTTTransport."""
        return self._transport

    @property
    def status(self) -> NodeStatus:
        """Get current node status."""
        return self._status

    @property
    def info(self) -> Optional[NodeInfo]:
        """Get node info from discovery."""
        return self._info

    @property
    def is_online(self) -> bool:
        """Check if node is online (heartbeat within timeout)."""
        if self._status.last_heartbeat == 0:
            return self._transport.is_connected

        elapsed = time.time() - self._status.last_heartbeat
        return elapsed < self._heartbeat_timeout_s

    @property
    def is_connected(self) -> bool:
        """Check if MQTT transport is connected."""
        return self._transport.is_connected

    @property
    def video_url(self) -> Optional[str]:
        """Get HTTP MJPEG video URL if available."""
        return self._video_url

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the transport and client."""
        await self._client.start()
        self._status.state = NodeState.ONLINE

    async def stop(self) -> None:
        """Stop the client and transport."""
        await self._client.stop()
        self._status.state = NodeState.OFFLINE

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_info(self, info: NodeInfo) -> None:
        """Set node info from discovery."""
        self._info = info
        self._status.state = info.state

        # Extract video URL from IP if available
        if info.ip:
            self._video_url = f"http://{info.ip}:81/stream"

    def set_video_url(self, url: str) -> None:
        """Set video stream URL."""
        self._video_url = url

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_heartbeat(self, data: dict) -> None:
        """Handle heartbeat events."""
        self._status.mark_heartbeat()
        self._status.state = NodeState.ONLINE

    def _on_telemetry(self, data: dict) -> None:
        """Handle telemetry events."""
        self._status.mark_seen()

    # ------------------------------------------------------------------
    # Convenience Methods (delegate to client)
    # ------------------------------------------------------------------

    async def arm(self) -> tuple[bool, Optional[str]]:
        """Arm the robot."""
        return await self._client.arm()

    async def disarm(self) -> tuple[bool, Optional[str]]:
        """Disarm the robot."""
        return await self._client.disarm()

    async def activate(self) -> tuple[bool, Optional[str]]:
        """Activate the robot."""
        return await self._client.activate()

    async def deactivate(self) -> tuple[bool, Optional[str]]:
        """Deactivate the robot."""
        return await self._client.deactivate()

    async def estop(self) -> tuple[bool, Optional[str]]:
        """Emergency stop."""
        return await self._client.estop()

    async def set_vel(self, vx: float, omega: float) -> tuple[bool, Optional[str]]:
        """Set velocity."""
        return await self._client.set_vel(vx, omega)

    async def send_reliable(
        self,
        cmd_type: str,
        payload: Optional[dict] = None,
        wait_for_ack: bool = True,
    ) -> tuple[bool, Optional[str]]:
        """Send a reliable command."""
        return await self._client.send_reliable(cmd_type, payload, wait_for_ack)

    async def send_stream(
        self,
        cmd_type: str,
        payload: dict,
        request_ack: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """Send streaming command."""
        return await self._client.send_stream(cmd_type, payload, request_ack)
