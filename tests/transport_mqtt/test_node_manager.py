# tests/transport_mqtt/test_node_manager.py
"""Tests for NodeManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from robot_host.core.event_bus import EventBus
from robot_host.transport.mqtt.node_manager import NodeManager
from robot_host.transport.mqtt.node_proxy import NodeProxy
from robot_host.transport.mqtt.models import NodeInfo, NodeState


class TestNodeManager:
    """Tests for NodeManager class."""

    def test_init(self):
        """Test manager initialization."""
        bus = EventBus()
        manager = NodeManager(
            bus=bus,
            broker_host="localhost",
            broker_port=1883,
        )

        assert manager.broker_host == "localhost"
        assert manager.broker_port == 1883
        assert len(manager.get_nodes()) == 0

    def test_init_with_failover(self):
        """Test initialization with failover broker."""
        bus = EventBus()
        manager = NodeManager(
            bus=bus,
            broker_host="primary.local",
            broker_port=1883,
            fallback_broker="fallback.local",
            fallback_port=1884,
        )

        assert manager._failover is not None
        assert manager._failover._primary.host == "primary.local"
        assert manager._failover._fallback.host == "fallback.local"

    def test_add_node(self):
        """Test adding a node."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        events = []
        bus.subscribe("node.added", lambda d: events.append(d))

        # Mock start to avoid actual connection
        with patch.object(NodeProxy, 'start', new_callable=AsyncMock):
            proxy = manager.add_node("node0", start=False)

        assert proxy is not None
        assert proxy.node_id == "node0"
        assert "node0" in manager.get_node_ids()
        assert len(events) == 1
        assert events[0]["node_id"] == "node0"

    def test_add_node_duplicate(self):
        """Test adding duplicate node returns existing."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        proxy1 = manager.add_node("node0", start=False)
        proxy2 = manager.add_node("node0", start=False)

        assert proxy1 is proxy2
        assert len(manager.get_nodes()) == 1

    @pytest.mark.asyncio
    async def test_remove_node(self):
        """Test removing a node."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        events = []
        bus.subscribe("node.removed", lambda d: events.append(d))

        manager.add_node("node0", start=False)
        assert "node0" in manager.get_node_ids()

        with patch.object(NodeProxy, 'stop', new_callable=AsyncMock):
            result = await manager.remove_node("node0")

        assert result is True
        assert "node0" not in manager.get_node_ids()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_remove_nonexistent_node(self):
        """Test removing a node that doesn't exist."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        result = await manager.remove_node("nonexistent")
        assert result is False

    def test_get_node(self):
        """Test getting a node by ID."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        manager.add_node("node0", start=False)

        assert manager.get_node("node0") is not None
        assert manager.get_node("nonexistent") is None

    def test_get_online_offline_nodes(self):
        """Test getting online and offline node lists."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        # Add nodes
        manager.add_node("node0", start=False)
        manager.add_node("node1", start=False)
        manager.add_node("node2", start=False)

        # Mock online status via _connected_evt (asyncio.Event)
        manager._nodes["node0"]._transport._connected_evt.set()
        manager._nodes["node1"]._transport._connected_evt.set()
        # node2 stays disconnected (event not set)

        online = manager.get_online_nodes()
        offline = manager.get_offline_nodes()

        assert "node0" in online
        assert "node1" in online
        assert "node2" in offline

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting command to all nodes."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        # Add nodes
        manager.add_node("node0", start=False)
        manager.add_node("node1", start=False)

        # Mock transport as connected via _connected_evt
        manager._nodes["node0"]._transport._connected_evt.set()
        manager._nodes["node1"]._transport._connected_evt.set()

        # Mock send_reliable
        for proxy in manager._nodes.values():
            proxy.send_reliable = AsyncMock(return_value=(True, None))

        results = await manager.broadcast("CMD_STOP", wait_for_ack=False)

        assert "node0" in results
        assert "node1" in results
        assert all(success for success, _ in results.values())

    @pytest.mark.asyncio
    async def test_broadcast_estop(self):
        """Test emergency stop broadcast."""
        bus = EventBus()
        manager = NodeManager(bus=bus, broker_host="localhost")

        manager.add_node("node0", start=False)
        manager._nodes["node0"]._transport._connected_evt.set()
        manager._nodes["node0"].send_reliable = AsyncMock(return_value=(True, None))

        results = await manager.broadcast_estop()

        manager._nodes["node0"].send_reliable.assert_called_with(
            "CMD_ESTOP", None, True
        )

    def test_health_check_detects_offline(self):
        """Test that health check detects offline nodes."""
        bus = EventBus()
        manager = NodeManager(
            bus=bus,
            broker_host="localhost",
            heartbeat_timeout_s=1.0,
        )

        events = []
        bus.subscribe("node.offline.node0", lambda d: events.append(d))

        manager.add_node("node0", start=False)

        # Simulate node was online
        proxy = manager._nodes["node0"]
        proxy._status.state = NodeState.ONLINE
        proxy._status.last_heartbeat = 0  # Very old

        manager._check_node_health()

        assert proxy._status.state == NodeState.OFFLINE
        assert len(events) == 1


class TestNodeProxy:
    """Tests for NodeProxy class."""

    def test_init(self):
        """Test proxy initialization."""
        bus = EventBus()
        proxy = NodeProxy(
            node_id="node0",
            broker_host="localhost",
            broker_port=1883,
            bus=bus,
        )

        assert proxy.node_id == "node0"
        assert proxy.client is not None
        assert proxy.transport is not None
        assert not proxy.is_online
        assert proxy.video_url is None

    def test_set_info(self):
        """Test setting node info."""
        bus = EventBus()
        proxy = NodeProxy(node_id="node0", broker_host="localhost", bus=bus)

        info = NodeInfo(
            node_id="node0",
            firmware="1.0.0",
            ip="192.168.1.100",
            state=NodeState.ONLINE,
        )

        proxy.set_info(info)

        assert proxy.info == info
        assert proxy._status.state == NodeState.ONLINE
        assert proxy.video_url == "http://192.168.1.100:81/stream"

    def test_set_video_url(self):
        """Test setting video URL."""
        bus = EventBus()
        proxy = NodeProxy(node_id="node0", broker_host="localhost", bus=bus)

        proxy.set_video_url("http://custom.url:8080/mjpeg")
        assert proxy.video_url == "http://custom.url:8080/mjpeg"

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        """Test convenience methods delegate to client."""
        bus = EventBus()
        proxy = NodeProxy(node_id="node0", broker_host="localhost", bus=bus)

        # Mock client methods
        proxy._client.arm = AsyncMock(return_value=(True, None))
        proxy._client.disarm = AsyncMock(return_value=(True, None))
        proxy._client.set_vel = AsyncMock(return_value=(True, None))

        await proxy.arm()
        proxy._client.arm.assert_called_once()

        await proxy.disarm()
        proxy._client.disarm.assert_called_once()

        await proxy.set_vel(0.5, 0.1)
        proxy._client.set_vel.assert_called_with(0.5, 0.1)
