# robot_host/mqtt/node_manager.py
"""
NodeManager - manages multiple nodes over MQTT.

Key fixes:
- Avoid race where NodeProxy.start() is launched in the background and the caller
  immediately tries to handshake/send commands before the MQTT transport is ready.
- Track per-node start tasks so callers can await readiness deterministically.
- In discover(auto_add=True), start nodes *synchronously* (await) by default so
  discovery returns with proxies actually started (transport connected + handshake attempted).
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional

from robot_host.core.event_bus import EventBus
from .models import NodeInfo, NodeState
from .node_proxy import NodeProxy
from .discovery import NodeDiscovery
from .broker_failover import BrokerFailover, BrokerConfig


class NodeManager:
    """
    Manages multiple ESP32 nodes over MQTT.

    Features:
    - Node discovery via fleet topics
    - Per-node proxies with AsyncRobotClient
    - Broker failover support
    - Online/offline tracking
    - Broadcast commands to all nodes

    Events published to EventBus:
    - node.discovered: New node found
    - node.online.{node_id}: Node came online
    - node.offline.{node_id}: Node went offline
    - node.added: Node proxy created
    - node.removed: Node proxy removed
    """

    def __init__(
        self,
        bus: EventBus,
        broker_host: str,
        broker_port: int = 1883,
        fallback_broker: Optional[str] = None,
        fallback_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        heartbeat_timeout_s: float = 5.0,
        health_check_interval_s: float = 1.0,
        require_version_match: bool = True,
    ) -> None:
        self._bus = bus
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._username = username
        self._password = password
        self._heartbeat_timeout_s = heartbeat_timeout_s
        self._health_check_interval_s = health_check_interval_s
        self._require_version_match = require_version_match

        # Node management
        self._nodes: Dict[str, NodeProxy] = {}
        self._node_last_seen: Dict[str, float] = {}

        # Track background start tasks to avoid races
        self._start_tasks: Dict[str, asyncio.Task] = {}

        # Discovery
        self._discovery = NodeDiscovery(
            bus=bus,
            broker_host=broker_host,
            broker_port=broker_port,
            username=username,
            password=password,
        )
        self._discovery.on_node_announce(self._on_node_discovered)

        # Broker failover
        self._failover: Optional[BrokerFailover] = None
        if fallback_broker:
            primary = BrokerConfig(
                host=broker_host,
                port=broker_port,
                username=username,
                password=password,
                name="primary",
            )
            fallback = BrokerConfig(
                host=fallback_broker,
                port=fallback_port,
                username=username,
                password=password,
                name="fallback",
            )
            self._failover = BrokerFailover(
                primary=primary,
                fallback=fallback,
                on_broker_change=self._on_broker_change,
            )

        # Tasks
        self._running = False
        self._health_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def broker_host(self) -> str:
        """Get current broker host."""
        if self._failover:
            return self._failover.current_broker.host
        return self._broker_host

    @property
    def broker_port(self) -> int:
        """Get current broker port."""
        if self._failover:
            return self._failover.current_broker.port
        return self._broker_port

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the node manager."""
        if self._running:
            return

        self._running = True

        # Start failover monitoring
        if self._failover:
            await self._failover.start()

        # Start discovery
        await self._discovery.start()

        # Start health check loop
        self._health_task = asyncio.create_task(self._health_check_loop())

        print("[NodeManager] Started")

    async def stop(self) -> None:
        """Stop the node manager and all nodes."""
        self._running = False

        # Stop health check
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        # Cancel any pending start tasks
        for node_id, task in list(self._start_tasks.items()):
            if not task.done():
                task.cancel()
            self._start_tasks.pop(node_id, None)

        # Stop all nodes
        for node_id in list(self._nodes.keys()):
            await self.remove_node(node_id)

        # Stop discovery
        await self._discovery.stop()

        # Stop failover
        if self._failover:
            await self._failover.stop()

        print("[NodeManager] Stopped")

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def add_node(self, node_id: str, start: bool = True) -> NodeProxy:
        """
        Add a node proxy for the given node_id.

        If the node already exists, returns the existing proxy.

        NOTE:
        - If start=True, start happens in the background (tracked by _start_tasks).
        - For deterministic "ready-to-use" behavior, call await start_node(node_id)
          or use discover(auto_add=True) which awaits starts by default.
        """
        if node_id in self._nodes:
            # Optionally kick off a start if requested and not already starting
            if start:
                self._ensure_start_task(self._nodes[node_id])
            return self._nodes[node_id]

        proxy = NodeProxy(
            node_id=node_id,
            broker_host=self.broker_host,
            broker_port=self.broker_port,
            bus=self._bus,
            username=self._username,
            password=self._password,
            heartbeat_timeout_s=self._heartbeat_timeout_s,
            require_version_match=self._require_version_match,
        )

        self._nodes[node_id] = proxy
        self._node_last_seen[node_id] = time.time()

        self._bus.publish("node.added", {"node_id": node_id})
        print(f"[NodeManager] Added node: {node_id}")

        if start:
            self._ensure_start_task(proxy)

        return proxy

    def _ensure_start_task(self, proxy: NodeProxy) -> None:
        """Ensure a background start task exists for this proxy."""
        node_id = proxy.node_id

        # If an existing task is running, do nothing
        existing = self._start_tasks.get(node_id)
        if existing and not existing.done():
            return

        self._start_tasks[node_id] = asyncio.create_task(self._start_node(proxy))

    async def _start_node(self, proxy: NodeProxy) -> None:
        """Start a node proxy (transport connect + handshake) with simple retry guard."""
        try:
            await proxy.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[NodeManager] Failed to start node {proxy.node_id}: {e}")

    async def start_node(self, node_id: str, timeout_s: float = 10.0) -> bool:
        """
        Deterministically start a node and wait for its start task to complete.

        Returns:
            True if the node is online after starting, else False.
        """
        proxy = self._nodes.get(node_id)
        if not proxy:
            return False

        # Ensure a start task exists
        self._ensure_start_task(proxy)

        task = self._start_tasks.get(node_id)
        if task is None:
            return False

        try:
            await asyncio.wait_for(task, timeout=timeout_s)
        except asyncio.TimeoutError:
            return False

        return proxy.is_online

    async def remove_node(self, node_id: str) -> bool:
        """Remove a node proxy."""
        if node_id not in self._nodes:
            return False

        # Cancel any pending start
        task = self._start_tasks.pop(node_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        proxy = self._nodes.pop(node_id)
        self._node_last_seen.pop(node_id, None)

        try:
            await proxy.stop()
        except Exception as e:
            print(f"[NodeManager] Error stopping node {node_id}: {e}")

        self._bus.publish("node.removed", {"node_id": node_id})
        print(f"[NodeManager] Removed node: {node_id}")
        return True

    def get_node(self, node_id: str) -> Optional[NodeProxy]:
        """Get a node proxy by ID."""
        return self._nodes.get(node_id)

    def get_nodes(self) -> List[NodeProxy]:
        """Get all node proxies."""
        return list(self._nodes.values())

    def get_node_ids(self) -> List[str]:
        """Get all node IDs."""
        return list(self._nodes.keys())

    def get_online_nodes(self) -> List[str]:
        """Get IDs of nodes that are currently online."""
        return [node_id for node_id, proxy in self._nodes.items() if proxy.is_online]

    def get_offline_nodes(self) -> List[str]:
        """Get IDs of nodes that are currently offline."""
        return [node_id for node_id, proxy in self._nodes.items() if not proxy.is_online]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, timeout_s: float = 5.0, auto_add: bool = True) -> List[NodeInfo]:
        """
        Discover nodes on the network.

        Args:
            timeout_s: How long to wait for responses
            auto_add: If True, automatically add discovered nodes AND await their start
                      so the caller can immediately interact with them.

        Returns:
            List of discovered NodeInfo
        """
        nodes = await self._discovery.discover(timeout_s)

        if auto_add:
            # IMPORTANT: don't background-start here; await starts so discovery returns "ready" nodes.
            for info in nodes:
                proxy = self.add_node(info.node_id, start=False)
                proxy.set_info(info)

                # Start deterministically (no race with handshake)
                try:
                    await proxy.start()
                except Exception as e:
                    print(f"[NodeManager] Failed to start node {info.node_id} after discovery: {e}")

        return nodes

    def _on_node_discovered(self, info: NodeInfo) -> None:
        """Handle node discovery callback."""
        if info.node_id in self._nodes:
            self._nodes[info.node_id].set_info(info)
            self._node_last_seen[info.node_id] = time.time()

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast(
        self,
        cmd_type: str,
        payload: Optional[dict] = None,
        wait_for_ack: bool = False,
    ) -> Dict[str, tuple[bool, Optional[str]]]:
        """
        Send a command to all online nodes.

        Returns dict mapping node_id to (success, error) tuple.
        """
        results: Dict[str, tuple[bool, Optional[str]]] = {}
        tasks = []

        for node_id, proxy in self._nodes.items():
            if proxy.is_online:
                task = asyncio.create_task(proxy.send_reliable(cmd_type, payload, wait_for_ack))
                tasks.append((node_id, task))

        for node_id, task in tasks:
            try:
                result = await task
                results[node_id] = result
            except Exception as e:
                results[node_id] = (False, str(e))

        return results

    async def broadcast_estop(self) -> Dict[str, tuple[bool, Optional[str]]]:
        """Emergency stop all nodes."""
        return await self.broadcast("CMD_ESTOP", wait_for_ack=True)

    async def broadcast_stop(self) -> Dict[str, tuple[bool, Optional[str]]]:
        """Stop all nodes."""
        return await self.broadcast("CMD_STOP", wait_for_ack=True)

    # ------------------------------------------------------------------
    # Health Monitoring
    # ------------------------------------------------------------------

    async def _health_check_loop(self) -> None:
        """Background task to monitor node health."""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval_s)
                self._check_node_health()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[NodeManager] Health check error: {e}")

    def _check_node_health(self) -> None:
        """Check health of all nodes."""
        for node_id, proxy in self._nodes.items():
            was_online = proxy.status.state == NodeState.ONLINE
            is_online = proxy.is_online

            if was_online and not is_online:
                proxy.status.state = NodeState.OFFLINE
                self._bus.publish(f"node.offline.{node_id}", {"node_id": node_id})
                print(f"[NodeManager] Node offline: {node_id}")

            elif not was_online and is_online:
                proxy.status.state = NodeState.ONLINE
                self._bus.publish(f"node.online.{node_id}", {"node_id": node_id})
                print(f"[NodeManager] Node online: {node_id}")

    # ------------------------------------------------------------------
    # Failover Handling
    # ------------------------------------------------------------------

    def _on_broker_change(self, broker: BrokerConfig) -> None:
        """Handle broker change event."""
        print(f"[NodeManager] Broker changed to: {broker.name} ({broker.host}:{broker.port})")
        asyncio.create_task(self._reconnect_all_nodes(broker))

    async def _reconnect_all_nodes(self, broker: BrokerConfig) -> None:
        """Reconnect all nodes to a new broker."""
        # Cancel any pending starts first
        for node_id, task in list(self._start_tasks.items()):
            if not task.done():
                task.cancel()
            self._start_tasks.pop(node_id, None)

        for node_id in list(self._nodes.keys()):
            proxy = self._nodes[node_id]

            try:
                await proxy.stop()
            except Exception:
                pass

            # Create new proxy with new broker
            new_proxy = NodeProxy(
                node_id=node_id,
                broker_host=broker.host,
                broker_port=broker.port,
                bus=self._bus,
                username=broker.username,
                password=broker.password,
                heartbeat_timeout_s=self._heartbeat_timeout_s,
                require_version_match=self._require_version_match,
            )

            # Preserve info
            if proxy.info:
                new_proxy.set_info(proxy.info)

            self._nodes[node_id] = new_proxy

            try:
                await new_proxy.start()
            except Exception as e:
                print(f"[NodeManager] Failed to reconnect {node_id}: {e}")
