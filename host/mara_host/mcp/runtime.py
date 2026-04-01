# mara_host/mcp/runtime.py
"""
Persistent runtime for MCP server.

Maintains connection to robot and provides state access with:
- Freshness tracking and staleness detection
- Command sequence correlation (sent → acked → observed)
- Event history for state transitions
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Any, Literal
from datetime import datetime, timedelta
from enum import Enum

# Fields that should be redacted in command history to prevent credential exposure
SENSITIVE_FIELDS = {"password", "secret", "token", "key", "credential", "auth"}


def _redact_sensitive(params: dict) -> dict:
    """Redact sensitive fields from a parameter dictionary."""
    return {
        k: "***REDACTED***" if k.lower() in SENSITIVE_FIELDS else v
        for k, v in params.items()
    }


# ═══════════════════════════════════════════════════════════════════════════
# Event Types
# ═══════════════════════════════════════════════════════════════════════════

class EventType(str, Enum):
    """Types of events tracked in the runtime."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STATE_CHANGE = "state_change"
    COMMAND_SENT = "command_sent"
    COMMAND_ACKED = "command_acked"
    COMMAND_FAILED = "command_failed"
    TELEMETRY = "telemetry"
    ERROR = "error"


@dataclass
class Event:
    """A runtime event with timestamp."""
    type: EventType
    timestamp: datetime
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Command Tracking
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CommandRecord:
    """Record of a command with full lifecycle tracking."""
    seq_id: int
    command: str
    params: dict
    sent_at: datetime
    acked_at: Optional[datetime] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "seq_id": self.seq_id,
            "command": self.command,
            "params": self.params,
            "sent_at": self.sent_at.isoformat(),
            "acked_at": self.acked_at.isoformat() if self.acked_at else None,
            "success": self.success,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


# ═══════════════════════════════════════════════════════════════════════════
# State Store with Freshness
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FreshValue:
    """A value with freshness tracking."""
    value: Any
    updated_at: datetime
    stale_after_s: float = 5.0  # Default staleness threshold

    @property
    def age_s(self) -> float:
        """Age in seconds since last update."""
        return (datetime.now() - self.updated_at).total_seconds()

    @property
    def is_stale(self) -> bool:
        """Check if value is stale."""
        return self.age_s > self.stale_after_s

    @property
    def freshness(self) -> Literal["fresh", "aging", "stale"]:
        """Get freshness status."""
        age = self.age_s
        if age < self.stale_after_s * 0.5:
            return "fresh"
        elif age < self.stale_after_s:
            return "aging"
        return "stale"

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "age_s": round(self.age_s, 2),
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class RuntimeSnapshot:
    connected: bool
    connected_at: str | None
    robot_state: dict[str, Any]
    firmware: str
    features: list[Any]
    imu: dict[str, Any] | None
    encoders: dict[int, dict[str, Any]]
    command_stats: dict[str, Any]
    recent_commands: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "connected_at": self.connected_at,
            "robot_state": self.robot_state,
            "firmware": self.firmware,
            "features": list(self.features),
            "imu": self.imu,
            "encoders": dict(self.encoders),
            "command_stats": self.command_stats,
            "recent_commands": list(self.recent_commands),
            "recent_events": list(self.recent_events),
        }


@dataclass(frozen=True)
class RuntimeFreshnessReport:
    robot_state: dict[str, Any]
    imu: dict[str, Any]
    encoders: dict[int, dict[str, Any]]
    any_stale: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "robot_state": self.robot_state,
            "imu": self.imu,
            "encoders": dict(self.encoders),
            "any_stale": self.any_stale,
        }


@dataclass(frozen=True)
class RuntimeHealthReport:
    connected: bool
    context_present: bool
    context_connected: bool
    robot_state: dict[str, Any]
    telemetry: dict[str, Any]
    commands: dict[str, Any]
    healthy: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "context_present": self.context_present,
            "context_connected": self.context_connected,
            "robot_state": self.robot_state,
            "telemetry": self.telemetry,
            "commands": self.commands,
            "healthy": self.healthy,
        }


@dataclass
class StateStore:
    """
    Canonical state store with freshness tracking.

    All state has explicit freshness so the LLM knows what's current.
    """
    # Connection state
    connected: bool = False
    connected_at: Optional[datetime] = None

    # Robot state (from firmware)
    robot_state: FreshValue = field(default_factory=lambda: FreshValue("UNKNOWN", datetime.now(), stale_after_s=2.0))

    # Identity (stable, long staleness)
    firmware_version: str = ""
    protocol_version: int = 0
    features: list = field(default_factory=list)

    # Telemetry (fast staleness - should update frequently)
    imu: FreshValue = field(default_factory=lambda: FreshValue(None, datetime.now(), stale_after_s=0.5))
    encoders: dict[int, FreshValue] = field(default_factory=dict)

    # Command tracking
    command_seq: int = 0
    commands: list[CommandRecord] = field(default_factory=list)
    pending_commands: dict[int, CommandRecord] = field(default_factory=dict)

    # Event history
    events: list[Event] = field(default_factory=list)

    # Limits
    max_commands: int = 100
    max_events: int = 200

    def next_seq(self) -> int:
        """Get next command sequence ID."""
        self.command_seq += 1
        return self.command_seq

    def add_event(self, event_type: EventType, data: dict = None) -> Event:
        """Add an event to history."""
        event = Event(
            type=event_type,
            timestamp=datetime.now(),
            data=data or {},
        )
        self.events.append(event)

        # Trim events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

        return event

    def get_recent_events(self, n: int = 10, event_type: EventType = None) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        events = self.events
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-n:]

    def get_command_stats(self) -> dict:
        """Get command statistics."""
        if not self.commands:
            return {"total": 0, "success_rate": 0, "avg_latency_ms": 0}

        successful = [c for c in self.commands if c.success]
        with_latency = [c for c in self.commands if c.latency_ms is not None]

        return {
            "total": len(self.commands),
            "successful": len(successful),
            "failed": len(self.commands) - len(successful),
            "success_rate": len(successful) / len(self.commands) if self.commands else 0,
            "avg_latency_ms": (
                sum(c.latency_ms for c in with_latency) / len(with_latency)
                if with_latency else 0
            ),
            "pending": len(self.pending_commands),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Runtime
# ═══════════════════════════════════════════════════════════════════════════

class MaraRuntime:
    """
    Persistent runtime for MCP server.

    Maintains a single connection to the robot and exposes
    services and state for MCP tools.

    Features:
    - Canonical state store with freshness tracking
    - Command sequence correlation (sent → acked)
    - Event history for state transitions
    - Service access layer
    """

    def __init__(
        self,
        port: Optional[str] = None,
        host: Optional[str] = None,
        ble_name: Optional[str] = None,
        tcp_port: int = 3333,
        robot_config: Optional[object] = None,
        robot_config_path: Optional[str] = None,
    ):
        self.port = port
        self.host = host
        self.ble_name = ble_name
        self.tcp_port = tcp_port
        self.robot_config = robot_config
        self.robot_config_path = robot_config_path

        self._ctx = None
        self._store = StateStore()
        self._lock = asyncio.Lock()

        # Robot abstraction layer (initialized via load_robot)
        self._robot_model = None
        self._robot_service = None
        self._robot_context = None

    @property
    def state(self) -> StateStore:
        """Get state store."""
        return self._store

    @property
    def is_connected(self) -> bool:
        """Check if connected to robot."""
        return self._ctx is not None and self._ctx.is_connected

    # ═══════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════

    async def connect(self) -> dict:
        """Connect to robot. Returns connection info."""
        from mara_host.cli.context import CLIContext

        async with self._lock:
            if self._ctx is not None and self._ctx.is_connected:
                return {"status": "already_connected"}

            # Recover from stale runtime contexts that still exist but no longer
            # hold a live client connection.
            if self._ctx is not None and not self._ctx.is_connected:
                try:
                    await self._ctx.disconnect()
                except Exception:
                    pass
                self._ctx = None

            ctx = CLIContext(
                port=self.port,
                host=self.host,
                ble_name=self.ble_name,
                tcp_port=self.tcp_port,
                verbose=False,
                robot_config=self.robot_config,
                robot_config_path=self.robot_config_path,
            )

            try:
                await ctx.connect()

                # Set up telemetry callbacks
                ctx._telemetry.on_imu(self._on_imu)
                ctx._telemetry.on_encoder(self._on_encoder)
                ctx._telemetry.on_state(self._on_state_change)

                self._ctx = ctx

                # Update state
                now = datetime.now()
                self._store.connected = True
                self._store.connected_at = now
                self._store.robot_state = FreshValue("ARMED", now, stale_after_s=2.0)
                self._store.firmware_version = self._ctx.client.firmware_version or ""
                self._store.protocol_version = self._ctx.client.protocol_version or 0
                self._store.features = self._ctx.client.features or []

                # Record event
                self._store.add_event(EventType.CONNECTED, {
                    "firmware": self._store.firmware_version,
                    "features": self._store.features,
                })

                return {
                    "status": "connected",
                    "firmware": self._store.firmware_version,
                    "features": self._store.features,
                }
            except Exception as e:
                try:
                    await ctx.disconnect()
                except Exception:
                    pass
                self._ctx = None
                self._store.connected = False
                self._store.add_event(EventType.ERROR, {
                    "stage": "connect",
                    "error": str(e),
                })
                raise

    async def disconnect(self) -> dict:
        """Disconnect from robot."""
        async with self._lock:
            if self._ctx is None:
                return {"status": "not_connected"}

            disconnect_error = None
            try:
                await self._ctx.disconnect()
            except Exception as e:
                disconnect_error = e
            finally:
                self._ctx = None
                self._store.connected = False
                self._store.robot_state = FreshValue("UNKNOWN", datetime.now(), stale_after_s=2.0)

                # Record event
                self._store.add_event(EventType.DISCONNECTED)
                if disconnect_error is not None:
                    self._store.add_event(EventType.ERROR, {
                        "stage": "disconnect",
                        "error": str(disconnect_error),
                    })

            return {"status": "disconnected"}

    async def ensure_connected(self) -> None:
        """Ensure connected, auto-connect if not."""
        if not self.is_connected:
            await self.connect()

    async def ensure_armed(self) -> None:
        """Ensure connected and armed for actuator commands."""
        await self.ensure_connected()
        # Use state_service for convergence with CLI/GUI
        result = await self.state_service.arm()
        if result.ok:
            self._store.robot_state = FreshValue("ARMED", datetime.now(), stale_after_s=2.0)
        # Small delay to let firmware state settle
        await asyncio.sleep(0.02)

    # ═══════════════════════════════════════════════════════════
    # Service Access
    # ═══════════════════════════════════════════════════════════

    @property
    def state_service(self):
        """Get StateService for state operations (arm/disarm/stop)."""
        if self._ctx:
            return self._ctx.state_service
        raise RuntimeError("Not connected")

    @property
    def servo_service(self):
        if self._ctx:
            return self._ctx.servo_service
        raise RuntimeError("Not connected")

    @property
    def motor_service(self):
        if self._ctx:
            return self._ctx.motor_service
        raise RuntimeError("Not connected")

    @property
    def composite_service(self):
        if self._ctx:
            from mara_host.services.control.composite_service import CompositeService
            return CompositeService(self._ctx.client)
        raise RuntimeError("Not connected")

    @property
    def gpio_service(self):
        if self._ctx:
            return self._ctx.gpio_service
        raise RuntimeError("Not connected")

    @property
    def stepper_service(self):
        if self._ctx:
            return self._ctx.stepper_service
        raise RuntimeError("Not connected")

    @property
    def encoder_service(self):
        if self._ctx:
            return self._ctx.encoder_service
        raise RuntimeError("Not connected")

    @property
    def i2c_service(self):
        if self._ctx:
            return self._ctx.i2c_service
        raise RuntimeError("Not connected")

    @property
    def imu_service(self):
        if self._ctx:
            return self._ctx.imu_service
        raise RuntimeError("Not connected")

    @property
    def ultrasonic_service(self):
        if self._ctx:
            return self._ctx.ultrasonic_service
        raise RuntimeError("Not connected")

    @property
    def pwm_service(self):
        if self._ctx:
            return self._ctx.pwm_service
        raise RuntimeError("Not connected")

    @property
    def wifi_service(self):
        if self._ctx:
            return self._ctx.wifi_service
        raise RuntimeError("Not connected")

    @property
    def control_graph_service(self):
        if self._ctx:
            return self._ctx.control_graph_service
        raise RuntimeError("Not connected")

    @property
    def mcu_diagnostics_service(self):
        if self._ctx:
            return self._ctx.mcu_diagnostics_service
        raise RuntimeError("Not connected")

    @property
    def motion_service(self):
        """Get MotionService for velocity control."""
        if self._ctx:
            return self._ctx.motion_service
        raise RuntimeError("Not connected")

    @property
    def signal_service(self):
        """Get SignalService for signal bus operations."""
        if self._ctx:
            return self._ctx.signal_service
        raise RuntimeError("Not connected")

    @property
    def camera_control_service(self):
        """Get CameraControlService for camera settings."""
        if self._ctx:
            return self._ctx.camera_control_service
        raise RuntimeError("Not connected")

    @property
    def controller_service(self):
        """Get ControllerService for control slots and observers."""
        if self._ctx:
            return self._ctx.controller_service
        raise RuntimeError("Not connected")

    @property
    def client(self):
        if self._ctx:
            return self._ctx.client
        raise RuntimeError("Not connected")

    @property
    def telemetry(self):
        if self._ctx:
            return self._ctx._telemetry
        raise RuntimeError("Not connected")

    # ═══════════════════════════════════════════════════════════
    # Robot Abstraction Layer
    # ═══════════════════════════════════════════════════════════

    @property
    def robot_loaded(self) -> bool:
        """Check if robot model is loaded."""
        return self._robot_service is not None

    @property
    def robot_service(self):
        """Get robot service for semantic control."""
        if not self._robot_service:
            raise RuntimeError("Robot not loaded. Call load_robot(config_path) first.")
        return self._robot_service

    @property
    def robot_context(self):
        """Get robot context for LLM state presentation."""
        if not self._robot_context:
            raise RuntimeError("Robot not loaded. Call load_robot(config_path) first.")
        return self._robot_context

    @property
    def robot_model(self):
        """Get robot model."""
        if not self._robot_model:
            raise RuntimeError("Robot not loaded. Call load_robot(config_path) first.")
        return self._robot_model

    async def load_robot(self, config_path: str) -> dict:
        """
        Load robot model and initialize robot abstraction layer.

        Call this after connect() to enable semantic robot control.

        Args:
            config_path: Path to robot YAML configuration file

        Returns:
            Dict with robot info (name, joints)
        """
        from mara_host.robot_layer import load_robot_model, RobotService, RobotStateContext

        # Load model from YAML
        self._robot_model = load_robot_model(config_path)

        # Create robot service (wraps existing hardware services)
        self._robot_service = RobotService(
            model=self._robot_model,
            servo_service=self.servo_service if self.is_connected else None,
            motor_service=self.motor_service if self.is_connected else None,
        )

        # Create context provider for LLM
        from mara_host.config import RobotConfig
        self.robot_config_path = config_path
        self.robot_config = RobotConfig.load(config_path)
        if self._ctx is not None:
            self._ctx.robot_config = self.robot_config
            self._ctx.robot_config_path = config_path
            self._ctx._policy_robot = None
            if self._ctx._control_graph_service is not None:
                self._ctx._control_graph_service.bind_sensor_policy_provider(self._ctx._sensor_policy_provider)

        self._robot_context = RobotStateContext(
            model=self._robot_model,
            pose_tracker=self._robot_service.pose,
            state_service=self.state_service if self.is_connected else None,
            telemetry_service=self._store,
        )

        return {
            "name": self._robot_model.name,
            "type": self._robot_model.type,
            "joints": list(self._robot_model.joints.keys()),
        }

    # ═══════════════════════════════════════════════════════════
    # Command Tracking
    # ═══════════════════════════════════════════════════════════

    def record_command(
        self,
        command: str,
        params: dict,
        success: bool,
        error: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ) -> CommandRecord:
        """
        Record a command with full tracking.

        Args:
            command: Command name
            params: Command parameters
            success: Whether command succeeded
            error: Error message if failed
            sent_at: When command was sent (for latency calculation)

        Returns the CommandRecord for correlation.
        """
        now = datetime.now()
        seq_id = self._store.next_seq()

        # Calculate latency if sent_at provided
        latency_ms = None
        if sent_at:
            latency_ms = (now - sent_at).total_seconds() * 1000

        # Redact sensitive fields before storing to prevent credential exposure
        safe_params = _redact_sensitive(params)

        record = CommandRecord(
            seq_id=seq_id,
            command=command,
            params=safe_params,
            sent_at=sent_at or now,
            acked_at=now,
            success=success,
            error=error,
            latency_ms=latency_ms,
        )

        self._store.commands.append(record)

        # Trim command history
        if len(self._store.commands) > self._store.max_commands:
            self._store.commands = self._store.commands[-self._store.max_commands:]

        # Record event
        event_type = EventType.COMMAND_ACKED if success else EventType.COMMAND_FAILED
        self._store.add_event(event_type, {
            "seq_id": seq_id,
            "command": command,
            "success": success,
            "error": error,
            "latency_ms": round(latency_ms, 2) if latency_ms else None,
        })

        return record

    # ═══════════════════════════════════════════════════════════
    # State Snapshots
    # ═══════════════════════════════════════════════════════════

    def sync_state_result(self, result) -> None:
        """Sync cached robot state from a successful StateService result."""
        if not getattr(result, "ok", False):
            return

        state = getattr(result, "state", None)
        if state:
            self._store.robot_state = FreshValue(state, datetime.now(), stale_after_s=2.0)

    def snapshot_model(self) -> RuntimeSnapshot:
        """Return the typed runtime snapshot model."""
        return RuntimeSnapshot(
            connected=self._store.connected,
            connected_at=(
                self._store.connected_at.isoformat()
                if self._store.connected_at else None
            ),
            robot_state=self._store.robot_state.to_dict(),
            firmware=self._store.firmware_version,
            features=list(self._store.features),
            imu=self._store.imu.to_dict() if self._store.imu.value else None,
            encoders={eid: ev.to_dict() for eid, ev in self._store.encoders.items()},
            command_stats=self._store.get_command_stats(),
            recent_commands=[c.to_dict() for c in self._store.commands[-5:]],
            recent_events=[e.to_dict() for e in self._store.get_recent_events(10)],
        )

    def get_snapshot(self) -> dict:
        """
        Get complete state snapshot for LLM context.

        Includes freshness information so the LLM knows what's current.
        """
        return self.snapshot_model().to_dict()

    def freshness_report_model(self) -> RuntimeFreshnessReport:
        """Return the typed runtime freshness report."""
        return RuntimeFreshnessReport(
            robot_state={
                "value": self._store.robot_state.value,
                "freshness": self._store.robot_state.freshness,
                "age_s": round(self._store.robot_state.age_s, 2),
            },
            imu={
                "has_data": self._store.imu.value is not None,
                "freshness": self._store.imu.freshness,
                "age_s": round(self._store.imu.age_s, 2),
            },
            encoders={
                eid: {
                    "freshness": ev.freshness,
                    "age_s": round(ev.age_s, 2),
                }
                for eid, ev in self._store.encoders.items()
            },
            any_stale=(
                self._store.robot_state.is_stale or
                self._store.imu.is_stale or
                any(ev.is_stale for ev in self._store.encoders.values())
            ),
        )

    def get_freshness_report(self) -> dict:
        """Get a report on data freshness."""
        return self.freshness_report_model().to_dict()

    def health_report_model(self) -> RuntimeHealthReport:
        """Return the typed runtime health report."""
        connected = self.is_connected
        imu_has_data = self._store.imu.value is not None
        encoder_count = len(self._store.encoders)
        recent_commands = self._store.commands[-5:]
        last_command = recent_commands[-1].to_dict() if recent_commands else None

        return RuntimeHealthReport(
            connected=connected,
            context_present=self._ctx is not None,
            context_connected=(self._ctx.is_connected if self._ctx is not None else False),
            robot_state=self._store.robot_state.to_dict(),
            telemetry={
                "imu": {
                    "has_data": imu_has_data,
                    "freshness": self._store.imu.freshness,
                    "age_s": round(self._store.imu.age_s, 2),
                },
                "encoders_seen": encoder_count,
                "encoder_ids": sorted(self._store.encoders.keys()),
            },
            commands={
                "stats": self._store.get_command_stats(),
                "last": last_command,
            },
            healthy=connected and not self._store.robot_state.is_stale,
        )

    def get_health_report(self) -> dict:
        """Get a compact runtime health report for HTTP callers."""
        return self.health_report_model().to_dict()

    # ═══════════════════════════════════════════════════════════
    # Telemetry Callbacks
    # ═══════════════════════════════════════════════════════════

    def _on_imu(self, imu_data) -> None:
        """Handle IMU telemetry."""
        self._store.imu = FreshValue(
            value={
                "ax": imu_data.ax,
                "ay": imu_data.ay,
                "az": imu_data.az,
                "gx": imu_data.gx,
                "gy": imu_data.gy,
                "gz": imu_data.gz,
            },
            updated_at=datetime.now(),
            stale_after_s=0.5,
        )

    def _on_encoder(self, encoder_data) -> None:
        """Handle encoder telemetry."""
        self._store.encoders[encoder_data.encoder_id] = FreshValue(
            value={
                "ticks": encoder_data.ticks,
                "velocity": encoder_data.velocity,
            },
            updated_at=datetime.now(),
            stale_after_s=0.5,
        )

    def _on_state_change(self, new_state: str) -> None:
        """Handle robot state change."""
        old_state = self._store.robot_state.value
        self._store.robot_state = FreshValue(new_state, datetime.now(), stale_after_s=2.0)

        # Record state transition event
        if old_state != new_state:
            self._store.add_event(EventType.STATE_CHANGE, {
                "from": old_state,
                "to": new_state,
            })
