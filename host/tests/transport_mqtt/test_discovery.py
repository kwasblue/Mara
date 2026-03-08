# tests/transport_mqtt/test_discovery.py
"""Tests for NodeDiscovery."""

import json

from mara_host.core.event_bus import EventBus
from mara_host.transport.mqtt.discovery import NodeDiscovery
from mara_host.transport.mqtt.models import NodeInfo, NodeState


class MockMessage:
    """Mock MQTT message."""

    def __init__(self, topic: str, payload: bytes):
        self.topic = topic
        self.payload = payload


class TestNodeDiscovery:
    """Tests for NodeDiscovery class."""

    def test_init(self):
        """Test discovery initialization."""
        bus = EventBus()
        discovery = NodeDiscovery(
            bus=bus,
            broker_host="localhost",
            broker_port=1883,
        )

        assert discovery._config.broker_host == "localhost"
        assert discovery._config.broker_port == 1883
        assert len(discovery._nodes) == 0

    def test_on_node_announce_callback(self):
        """Test registering node announce callback."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        callback_data = []
        discovery.on_node_announce(lambda info: callback_data.append(info))

        # Simulate discovery response
        response = {
            "node_id": "node0",
            "robot_id": "mara-001",
            "firmware": "1.0.0",
            "protocol": 2,
            "board": "esp32",
            "state": "online",
            "ip": "192.168.1.100",
        }

        msg = MockMessage("mara/fleet/discover_response", json.dumps(response).encode())
        discovery._on_message(msg)

        assert len(callback_data) == 1
        assert callback_data[0].node_id == "node0"
        assert callback_data[0].firmware == "1.0.0"

    def test_on_message_parses_response(self):
        """Test that discovery messages are parsed correctly."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        events = []
        bus.subscribe("node.discovered", lambda d: events.append(("discovered", d)))
        bus.subscribe("node.online.node0", lambda d: events.append(("online", d)))

        response = {
            "node_id": "node0",
            "robot_id": "mara-001",
            "firmware": "1.0.0",
            "protocol": 2,
            "board": "esp32s3",
            "state": "online",
            "ip": "10.0.0.50",
            "features": ["servo", "encoder"],
        }

        msg = MockMessage("mara/fleet/discover_response", json.dumps(response).encode())
        discovery._on_message(msg)

        # Check node was added
        assert "node0" in discovery._nodes
        info = discovery._nodes["node0"]
        assert info.robot_id == "mara-001"
        assert info.board == "esp32s3"
        assert info.ip == "10.0.0.50"
        assert "servo" in info.features
        assert info.state == NodeState.ONLINE

        # Check events were published
        assert len(events) == 2
        assert events[0][0] == "discovered"
        assert events[1][0] == "online"

    def test_on_message_updates_existing_node(self):
        """Test that existing nodes are updated."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        events = []
        bus.subscribe("node.discovered", lambda d: events.append(d))

        # First discovery
        response1 = {"node_id": "node0", "firmware": "1.0.0", "state": "online"}
        discovery._on_message(MockMessage("", json.dumps(response1).encode()))

        # Second discovery (same node)
        response2 = {"node_id": "node0", "firmware": "1.1.0", "state": "online"}
        discovery._on_message(MockMessage("", json.dumps(response2).encode()))

        # Should only fire discovered event once
        assert len(events) == 1

        # But info should be updated
        assert discovery._nodes["node0"].firmware == "1.1.0"

    def test_get_known_nodes(self):
        """Test getting list of known nodes."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        # Add some nodes
        for i in range(3):
            response = {"node_id": f"node{i}", "firmware": "1.0.0", "state": "online"}
            discovery._on_message(MockMessage("", json.dumps(response).encode()))

        nodes = discovery.get_known_nodes()
        assert len(nodes) == 3
        assert {n.node_id for n in nodes} == {"node0", "node1", "node2"}

    def test_get_node(self):
        """Test getting specific node."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        response = {"node_id": "robot1", "firmware": "2.0.0", "state": "online"}
        discovery._on_message(MockMessage("", json.dumps(response).encode()))

        node = discovery.get_node("robot1")
        assert node is not None
        assert node.firmware == "2.0.0"

        assert discovery.get_node("nonexistent") is None

    def test_on_message_handles_invalid_json(self):
        """Test handling of invalid JSON gracefully (no crash)."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        msg = MockMessage("", b"not valid json")
        # Should not raise - handles gracefully
        discovery._on_message(msg)
        # No nodes should be added
        assert len(discovery.get_known_nodes()) == 0

    def test_on_message_handles_missing_node_id(self):
        """Test handling of response without node_id."""
        bus = EventBus()
        discovery = NodeDiscovery(bus=bus, broker_host="localhost")

        response = {"firmware": "1.0.0"}  # Missing node_id
        msg = MockMessage("", json.dumps(response).encode())
        discovery._on_message(msg)

        assert len(discovery._nodes) == 0


class TestNodeInfo:
    """Tests for NodeInfo model."""

    def test_from_discovery_response(self):
        """Test creating NodeInfo from discovery response."""
        data = {
            "robot_id": "mara-001",
            "firmware": "1.2.3",
            "protocol": 2,
            "board": "esp32s3",
            "state": "online",
            "ip": "192.168.1.50",
            "features": ["camera", "imu"],
        }

        info = NodeInfo.from_discovery_response("node0", data)

        assert info.node_id == "node0"
        assert info.robot_id == "mara-001"
        assert info.firmware == "1.2.3"
        assert info.protocol == 2
        assert info.board == "esp32s3"
        assert info.state == NodeState.ONLINE
        assert info.ip == "192.168.1.50"
        assert info.features == ["camera", "imu"]

    def test_from_discovery_response_minimal(self):
        """Test creating NodeInfo with minimal data."""
        data = {}

        info = NodeInfo.from_discovery_response("node1", data)

        assert info.node_id == "node1"
        assert info.robot_id is None
        assert info.firmware is None
        assert info.state == NodeState.UNKNOWN
        assert info.features == []
