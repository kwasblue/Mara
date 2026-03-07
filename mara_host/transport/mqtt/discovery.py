# mara_host/mqtt/discovery.py
"""
Node discovery over MQTT fleet topics.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable, List, Optional

import aiomqtt

from mara_host.core.event_bus import EventBus
from .models import (
    MQTTConfig,
    NodeInfo,
    NodeState,
    get_discover_topic,
    get_discover_response_topic,
)


class NodeDiscovery:
    """
    Discovers ESP32 nodes via MQTT fleet discovery protocol.

    Protocol:
    1. Host publishes to mara/fleet/discover (empty or JSON)
    2. Nodes respond to mara/fleet/discover_response with JSON:
       {
         "robot_id": "...",
         "node_id": "...",
         "firmware": "...",
         "protocol": N,
         "board": "...",
         "state": "online" | "ONLINE" | ...,
         "ip": "...",
         "features": [...]
       }
    """

    def __init__(
        self,
        bus: EventBus,
        broker_host: str,
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        *,
        debug: bool = False,
        use_versioned_topics: bool = False,
    ) -> None:
        self._bus = bus
        self._config = MQTTConfig(
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password,
            client_id="host-discovery",
        )

        # Topic configuration
        self._discover_topic = get_discover_topic(versioned=use_versioned_topics)
        self._discover_response_topic = get_discover_response_topic(versioned=use_versioned_topics)

        self._client: Optional[aiomqtt.Client] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_node_announce: Optional[Callable[[NodeInfo], None]] = None

        # Known nodes
        self._nodes: dict[str, NodeInfo] = {}

        # Connection readiness (so discover() doesn't race connect)
        self._connected_evt = asyncio.Event()

        self._debug = debug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start listening for discovery responses."""
        if self._task is not None:
            return

        self._running = True
        self._connected_evt.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop discovery listener."""
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

    async def discover(
        self,
        timeout_s: float = 5.0,
        keep_alive: bool = False,
    ) -> List[NodeInfo]:
        """
        Send discovery request and collect responses.

        Args:
            timeout_s: How long to wait for responses
            keep_alive: If True, keep discovery connection open for continuous
                       monitoring. If False (default), connection is managed
                       by NodeManager which stops it after scan.

        Returns list of discovered nodes within timeout.

        For large fleets (100+ nodes):
        - Use keep_alive=True to avoid connection churn
        - Consider multiple discover() calls with shorter timeouts
        - Use on_node_announce() callback for streaming discovery
        """
        # Use set for O(1) deduplication instead of O(n) list search
        discovered_ids: set[str] = set()
        discovered: List[NodeInfo] = []

        def on_discover(info: NodeInfo) -> None:
            if info.node_id not in discovered_ids:
                discovered_ids.add(info.node_id)
                discovered.append(info)

        old_callback = self._on_node_announce
        self._on_node_announce = on_discover

        try:
            if not self._running:
                await self.start()

            # Wait until connection is actually established (or time out early)
            try:
                await asyncio.wait_for(self._connected_evt.wait(), timeout=min(2.0, timeout_s))
            except asyncio.TimeoutError:
                if self._debug:
                    print("[NodeDiscovery][DEBUG] connect wait timed out; still trying...")

            await self._send_discover_request()

            # Collect responses
            await asyncio.sleep(timeout_s)

        finally:
            self._on_node_announce = old_callback

        return discovered

    async def discover_continuous(
        self,
        on_node: Callable[[NodeInfo], None],
        interval_s: float = 10.0,
    ) -> None:
        """
        Continuously discover nodes at regular intervals.

        This is more efficient for large fleets than repeated discover() calls
        because it keeps the MQTT connection open.

        Args:
            on_node: Callback for each discovered node
            interval_s: How often to send discovery requests

        Call stop() to end continuous discovery.
        """
        if not self._running:
            await self.start()

        self._on_node_announce = on_node

        while self._running:
            try:
                await asyncio.wait_for(self._connected_evt.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            await self._send_discover_request()
            await asyncio.sleep(interval_s)

    def on_node_announce(self, callback: Callable[[NodeInfo], None]) -> None:
        """Register callback for node announcements."""
        self._on_node_announce = callback

    def get_known_nodes(self) -> List[NodeInfo]:
        """Get list of all known nodes."""
        return list(self._nodes.values())

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """Get info for a specific node."""
        return self._nodes.get(node_id)

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        """Main connection loop."""
        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._connected_evt.clear()
                # Suppress common disconnect errors during normal operation
                err_str = str(e).lower()
                if "disconnect" in err_str or "iteration" in err_str:
                    pass  # Normal during shutdown or broker hiccup
                elif self._running:
                    print(f"[NodeDiscovery] Error: {e}")

            if self._running:
                await asyncio.sleep(2.0)

    async def _connect_and_listen(self) -> None:
        """Connect and listen for discovery responses."""
        print(f"[NodeDiscovery] Connecting to {self._config.broker_host}:{self._config.broker_port}...")

        async with aiomqtt.Client(
            hostname=self._config.broker_host,
            port=self._config.broker_port,
            username=self._config.username,
            password=self._config.password,
            identifier=self._config.client_id,
            clean_session=True,
            keepalive=self._config.keepalive,
        ) as client:
            self._client = client
            self._connected_evt.set()
            print("[NodeDiscovery] Connected, subscribing to discovery responses...")

            await client.subscribe(self._discover_response_topic, qos=1)

            async for message in client.messages:
                if not self._running:
                    break
                self._on_message(message)

        # leaving context manager => disconnected
        self._client = None
        self._connected_evt.clear()

    async def _send_discover_request(self) -> None:
        """Send fleet discovery request."""
        if not self._client:
            print("[NodeDiscovery] Cannot send discover: not connected")
            return

        try:
            await self._client.publish(self._discover_topic, b"{}", qos=1)
            print("[NodeDiscovery] Sent discovery request")
        except asyncio.TimeoutError:
            print("[NodeDiscovery] Failed to send discover: Operation timed out")
        except Exception as e:
            print(f"[NodeDiscovery] Failed to send discover: {e}")

    # ------------------------
    # Normalization helpers
    # ------------------------

    def _normalize_discovery_payload(self, data: dict) -> tuple[Optional[str], dict]:
        """
        Normalize discovery JSON so the rest of the host stack can remain strict.

        Returns (node_id, normalized_data).
        """
        # 1) node identity: prefer node_id, else robot_id, else id
        node_id = data.get("node_id") or data.get("robot_id") or data.get("id")

        # 2) normalize state for NodeState enum (expects 'online', 'offline', ...)
        if "state" in data and isinstance(data["state"], str):
            data["state"] = data["state"].strip().lower()

        return node_id, data

    def _on_message(self, message: aiomqtt.Message) -> None:
        """Handle discovery response."""
        try:
            payload = message.payload
            if isinstance(payload, (bytes, bytearray)):
                raw = payload.decode("utf-8", errors="replace")
            else:
                raw = str(payload)

            if self._debug:
                print(f"[NodeDiscovery][DEBUG] RX topic={getattr(message, 'topic', '?')} payload={raw!r}")

            data = json.loads(raw)

            node_id, data = self._normalize_discovery_payload(data)
            if not node_id:
                if self._debug:
                    print("[NodeDiscovery][DEBUG] Missing node_id (node_id/robot_id/id)")
                return

            # If state is unknown/unset, NodeInfo will default to UNKNOWN; if it is
            # present but weird, NodeInfo.from_discovery_response may throw ValueError.
            # We keep models strict, so catch and downgrade to UNKNOWN here.
            try:
                info = NodeInfo.from_discovery_response(node_id, data)
            except ValueError as ve:
                # Most common: NodeState(value) failure
                if self._debug:
                    print(f"[NodeDiscovery][DEBUG] ValueError parsing NodeInfo: {ve}. Forcing state=unknown.")
                data2 = dict(data)
                data2["state"] = "unknown"
                info = NodeInfo.from_discovery_response(node_id, data2)

            # Mark online because we literally received a response
            info.state = NodeState.ONLINE

            # Update known nodes
            is_new = node_id not in self._nodes
            self._nodes[node_id] = info

            # Publish events
            if is_new:
                self._bus.publish("node.discovered", {"node_id": node_id, "info": info})
            self._bus.publish(f"node.online.{node_id}", {"info": info})

            # Call callback
            if self._on_node_announce:
                self._on_node_announce(info)

        except json.JSONDecodeError as e:
            if self._debug:
                print(f"[NodeDiscovery][DEBUG] JSON decode failed: {e}")
        except Exception as e:
            print(f"[NodeDiscovery] Failed to handle response: {e}")
