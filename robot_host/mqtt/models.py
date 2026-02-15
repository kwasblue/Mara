# robot_host/mqtt/models.py
"""
Data models for MQTT transport and node management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import time


class NodeState(Enum):
    """Node connection state."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"


@dataclass
class MQTTConfig:
    """MQTT connection configuration."""
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    keepalive: int = 60
    clean_session: bool = True


@dataclass
class NodeInfo:
    """
    Information about a discovered node.

    Matches firmware discovery response format.
    """
    node_id: str
    robot_id: Optional[str] = None
    firmware: Optional[str] = None
    protocol: Optional[int] = None
    board: Optional[str] = None
    state: NodeState = NodeState.UNKNOWN
    ip: Optional[str] = None
    features: List[str] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)

    @classmethod
    def from_discovery_response(cls, node_id: str, data: dict) -> "NodeInfo":
        """Create NodeInfo from firmware discovery response JSON."""
        return cls(
            node_id=node_id,
            robot_id=data.get("robot_id"),
            firmware=data.get("firmware"),
            protocol=data.get("protocol"),
            board=data.get("board"),
            state=NodeState(data.get("state", "unknown")),
            ip=data.get("ip"),
            features=data.get("features", []),
        )


@dataclass
class NodeStatus:
    """Runtime status of a node."""
    node_id: str
    state: NodeState = NodeState.UNKNOWN
    last_seen: float = 0.0
    last_heartbeat: float = 0.0
    message_count: int = 0
    error_count: int = 0
    latency_ms: Optional[float] = None

    @property
    def is_online(self) -> bool:
        return self.state == NodeState.ONLINE

    def mark_seen(self) -> None:
        """Update last_seen timestamp."""
        self.last_seen = time.time()
        self.message_count += 1

    def mark_heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self.last_heartbeat = time.time()
        self.last_seen = self.last_heartbeat

    def mark_error(self) -> None:
        """Increment error count."""
        self.error_count += 1


# MQTT topic templates matching firmware
TOPIC_CMD = "mara/{node_id}/cmd"
TOPIC_ACK = "mara/{node_id}/ack"
TOPIC_TELEMETRY = "mara/{node_id}/telemetry"
TOPIC_STATE = "mara/{node_id}/state"
TOPIC_FLEET_DISCOVER = "mara/fleet/discover"
TOPIC_FLEET_DISCOVER_RESPONSE = "mara/fleet/discover_response"


def get_cmd_topic(node_id: str) -> str:
    """Get command topic for a node."""
    return TOPIC_CMD.format(node_id=node_id)


def get_ack_topic(node_id: str) -> str:
    """Get ack topic for a node."""
    return TOPIC_ACK.format(node_id=node_id)


def get_telemetry_topic(node_id: str) -> str:
    """Get telemetry topic for a node."""
    return TOPIC_TELEMETRY.format(node_id=node_id)


def get_state_topic(node_id: str) -> str:
    """Get state topic for a node."""
    return TOPIC_STATE.format(node_id=node_id)
