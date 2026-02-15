# robot_host/transport/mqtt/__init__.py
"""
MQTT transport and multi-node management for ESP32 communication.

This module provides:
- MQTTTransport: Transport layer implementing HasSendBytes for AsyncRobotClient
- NodeProxy: Per-node wrapper combining transport + client
- NodeManager: Multi-node orchestration with discovery and failover
- NodeDiscovery: Fleet-wide node discovery

Example usage (single node):
    from robot_host.transport.mqtt import MQTTTransport
    from robot_host.command.client import AsyncRobotClient

    transport = MQTTTransport(
        broker_host="192.168.1.100",
        node_id="node0",
    )
    client = AsyncRobotClient(transport)
    await client.start()
    await client.arm()

Example usage (multi-node):
    from robot_host.transport.mqtt import NodeManager
    from robot_host.core.event_bus import EventBus

    bus = EventBus()
    manager = NodeManager(
        bus=bus,
        broker_host="192.168.1.100",
        fallback_broker="192.168.1.1",  # Node0's built-in broker
    )
    await manager.start()

    # Discover nodes
    nodes = await manager.discover(timeout_s=5.0)

    # Get specific node
    node0 = manager.get_node("node0")
    await node0.client.arm()

    # Broadcast to all
    await manager.broadcast("CMD_STOP")
"""

from .models import (
    MQTTConfig,
    NodeInfo,
    NodeStatus,
    NodeState,
    TOPIC_CMD,
    TOPIC_ACK,
    TOPIC_TELEMETRY,
    TOPIC_STATE,
    TOPIC_FLEET_DISCOVER,
    TOPIC_FLEET_DISCOVER_RESPONSE,
    get_cmd_topic,
    get_ack_topic,
    get_telemetry_topic,
    get_state_topic,
)
from .transport import MQTTTransport
from .discovery import NodeDiscovery
from .node_proxy import NodeProxy
from .node_manager import NodeManager
from .broker_failover import BrokerFailover, BrokerConfig, BrokerState

__all__ = [
    # Core transport
    "MQTTTransport",

    # Node management
    "NodeProxy",
    "NodeManager",
    "NodeDiscovery",

    # Failover
    "BrokerFailover",
    "BrokerConfig",
    "BrokerState",

    # Models
    "MQTTConfig",
    "NodeInfo",
    "NodeStatus",
    "NodeState",

    # Topic constants
    "TOPIC_CMD",
    "TOPIC_ACK",
    "TOPIC_TELEMETRY",
    "TOPIC_STATE",
    "TOPIC_FLEET_DISCOVER",
    "TOPIC_FLEET_DISCOVER_RESPONSE",

    # Topic helpers
    "get_cmd_topic",
    "get_ack_topic",
    "get_telemetry_topic",
    "get_state_topic",
]
