# mara_host/mcp/runtime.py
"""
Persistent runtime for MCP server.

Maintains connection to robot and provides state access.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class CommandRecord:
    """Record of a command sent to the robot."""
    command: str
    params: dict
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class RuntimeState:
    """Current runtime state - always fresh."""
    connected: bool = False
    robot_state: str = "UNKNOWN"
    firmware_version: str = ""
    protocol_version: int = 0
    features: list = field(default_factory=list)

    # Latest telemetry
    imu: Optional[dict] = None
    encoders: dict = field(default_factory=dict)

    # Command history (last N)
    command_history: list = field(default_factory=list)

    # Timestamps
    connected_at: Optional[datetime] = None
    last_telemetry_at: Optional[datetime] = None
    last_command_at: Optional[datetime] = None


class MaraRuntime:
    """
    Persistent runtime for MCP server.

    Maintains a single connection to the robot and exposes
    services and state for MCP tools.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        host: Optional[str] = None,
        tcp_port: int = 3333,
    ):
        self.port = port
        self.host = host
        self.tcp_port = tcp_port

        self._ctx = None
        self._state = RuntimeState()
        self._command_history_limit = 50
        self._lock = asyncio.Lock()

    @property
    def state(self) -> RuntimeState:
        """Get current runtime state."""
        return self._state

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
            if self._ctx is not None:
                return {"status": "already_connected"}

            self._ctx = CLIContext(
                port=self.port,
                host=self.host,
                tcp_port=self.tcp_port,
                verbose=False,
            )

            await self._ctx.connect()

            # Set up telemetry callbacks
            self._ctx._telemetry.on_imu(self._on_imu)
            self._ctx._telemetry.on_encoder(self._on_encoder)
            self._ctx._telemetry.on_state(self._on_state_change)

            # Update state
            self._state.connected = True
            self._state.connected_at = datetime.now()
            self._state.robot_state = "ARMED"  # CLIContext auto-arms
            self._state.firmware_version = self._ctx.client.firmware_version or ""
            self._state.protocol_version = self._ctx.client.protocol_version or 0
            self._state.features = self._ctx.client.features or []

            return {
                "status": "connected",
                "firmware": self._state.firmware_version,
                "features": self._state.features,
            }

    async def disconnect(self) -> dict:
        """Disconnect from robot."""
        async with self._lock:
            if self._ctx is None:
                return {"status": "not_connected"}

            await self._ctx.disconnect()
            self._ctx = None

            self._state.connected = False
            self._state.robot_state = "UNKNOWN"

            return {"status": "disconnected"}

    async def ensure_connected(self) -> None:
        """Ensure connected, auto-connect if not."""
        if not self.is_connected:
            await self.connect()

    async def ensure_armed(self) -> None:
        """Ensure connected and armed for actuator commands."""
        await self.ensure_connected()
        # Always send arm command - firmware should handle idempotent arms
        # This ensures we're armed even if firmware auto-disarmed
        ok, err = await self.client.arm()
        if ok:
            self._state.robot_state = "ARMED"
        # Small delay to let firmware state settle
        await asyncio.sleep(0.02)

    # ═══════════════════════════════════════════════════════════
    # Service Access
    # ═══════════════════════════════════════════════════════════

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
    def imu_service(self):
        if self._ctx:
            return self._ctx.imu_service
        raise RuntimeError("Not connected")

    @property
    def pwm_service(self):
        if self._ctx:
            return self._ctx.pwm_service
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
    # State Access
    # ═══════════════════════════════════════════════════════════

    def get_snapshot(self) -> dict:
        """Get complete state snapshot for LLM context."""
        return {
            "connected": self._state.connected,
            "robot_state": self._state.robot_state,
            "firmware": self._state.firmware_version,
            "features": self._state.features,
            "imu": self._state.imu,
            "encoders": self._state.encoders,
            "last_telemetry": (
                self._state.last_telemetry_at.isoformat()
                if self._state.last_telemetry_at else None
            ),
            "recent_commands": [
                {
                    "command": c.command,
                    "params": c.params,
                    "success": c.success,
                    "error": c.error,
                }
                for c in self._state.command_history[-5:]
            ],
        }

    def record_command(
        self,
        command: str,
        params: dict,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a command in history."""
        record = CommandRecord(
            command=command,
            params=params,
            timestamp=datetime.now(),
            success=success,
            error=error,
        )
        self._state.command_history.append(record)
        self._state.last_command_at = record.timestamp

        # Trim history
        if len(self._state.command_history) > self._command_history_limit:
            self._state.command_history = self._state.command_history[-self._command_history_limit:]

    # ═══════════════════════════════════════════════════════════
    # Telemetry Callbacks
    # ═══════════════════════════════════════════════════════════

    def _on_imu(self, imu_data) -> None:
        """Handle IMU telemetry."""
        self._state.imu = {
            "ax": imu_data.ax,
            "ay": imu_data.ay,
            "az": imu_data.az,
            "gx": imu_data.gx,
            "gy": imu_data.gy,
            "gz": imu_data.gz,
        }
        self._state.last_telemetry_at = datetime.now()

    def _on_encoder(self, encoder_data) -> None:
        """Handle encoder telemetry."""
        self._state.encoders[encoder_data.encoder_id] = {
            "ticks": encoder_data.ticks,
            "velocity": encoder_data.velocity,
        }
        self._state.last_telemetry_at = datetime.now()

    def _on_state_change(self, new_state: str) -> None:
        """Handle robot state change."""
        self._state.robot_state = new_state
