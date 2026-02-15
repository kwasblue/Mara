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


# MQTT topic version for protocol evolution
# Change this when making breaking protocol changes
TOPIC_VERSION = "v1"

# MQTT topic templates matching firmware
# Version prefix enables gradual migration between protocol versions
TOPIC_PREFIX = f"mara/{TOPIC_VERSION}"
TOPIC_CMD = f"{TOPIC_PREFIX}/{{node_id}}/cmd"
TOPIC_ACK = f"{TOPIC_PREFIX}/{{node_id}}/ack"
TOPIC_TELEMETRY = f"{TOPIC_PREFIX}/{{node_id}}/telemetry"
TOPIC_STATE = f"{TOPIC_PREFIX}/{{node_id}}/state"
TOPIC_FLEET_DISCOVER = f"{TOPIC_PREFIX}/fleet/discover"
TOPIC_FLEET_DISCOVER_RESPONSE = f"{TOPIC_PREFIX}/fleet/discover_response"

# Legacy topics (v0 - no version prefix) for backwards compatibility
TOPIC_CMD_LEGACY = "mara/{node_id}/cmd"
TOPIC_ACK_LEGACY = "mara/{node_id}/ack"
TOPIC_TELEMETRY_LEGACY = "mara/{node_id}/telemetry"
TOPIC_FLEET_DISCOVER_LEGACY = "mara/fleet/discover"
TOPIC_FLEET_DISCOVER_RESPONSE_LEGACY = "mara/fleet/discover_response"


def get_cmd_topic(node_id: str, versioned: bool = False) -> str:
    """Get command topic for a node.

    Args:
        node_id: The node identifier
        versioned: If True, use versioned topic (mara/v1/{node}/cmd).
                  If False (default), use legacy topic (mara/{node}/cmd).
    """
    template = TOPIC_CMD if versioned else TOPIC_CMD_LEGACY
    return template.format(node_id=node_id)


def get_ack_topic(node_id: str, versioned: bool = False) -> str:
    """Get ack topic for a node."""
    template = TOPIC_ACK if versioned else TOPIC_ACK_LEGACY
    return template.format(node_id=node_id)


def get_telemetry_topic(node_id: str, versioned: bool = False) -> str:
    """Get telemetry topic for a node."""
    template = TOPIC_TELEMETRY if versioned else TOPIC_TELEMETRY_LEGACY
    return template.format(node_id=node_id)


def get_state_topic(node_id: str, versioned: bool = False) -> str:
    """Get state topic for a node."""
    template = TOPIC_STATE if versioned else "mara/{node_id}/state"
    return template.format(node_id=node_id)


def get_discover_topic(versioned: bool = False) -> str:
    """Get fleet discovery topic."""
    return TOPIC_FLEET_DISCOVER if versioned else TOPIC_FLEET_DISCOVER_LEGACY


def get_discover_response_topic(versioned: bool = False) -> str:
    """Get fleet discovery response topic."""
    return TOPIC_FLEET_DISCOVER_RESPONSE if versioned else TOPIC_FLEET_DISCOVER_RESPONSE_LEGACY
