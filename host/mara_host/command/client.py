# mara_host/core/client.py

from __future__ import annotations
import contextlib
import json
import asyncio
import inspect
import time
from typing import Optional, Protocol, Callable, Dict, Any, Tuple

from mara_host.core.event_bus import EventBus
from mara_host.core import protocol
from .coms.connection_monitor import ConnectionMonitor
from .coms.reliable_commander import ReliableCommander
from mara_host.config.client_commands import RobotCommandsMixin
from mara_host.telemetry.binary_parser import parse_telemetry_bin
from mara_host.config.version import PROTOCOL_VERSION
from .binary_mixin import BinaryCommandsMixin

class HasSendBytes(Protocol):
    """Minimal transport interface used by the async robot client."""

    async def send_bytes(self, data: bytes) -> None: ...
    def set_frame_handler(self, handler: Callable[[bytes], None]) -> None: ...
    def start(self) -> object: ...
    def stop(self) -> object: ...


# Re-export / alias protocol constants for convenience
MSG_PING             = protocol.MSG_PING
MSG_PONG             = protocol.MSG_PONG
MSG_HEARTBEAT        = protocol.MSG_HEARTBEAT
MSG_WHOAMI           = protocol.MSG_WHOAMI
MSG_CMD_JSON         = protocol.MSG_CMD_JSON
MSG_CMD_BIN          = protocol.MSG_CMD_BIN
MSG_VERSION_REQUEST  = protocol.MSG_VERSION_REQUEST
MSG_VERSION_RESPONSE = protocol.MSG_VERSION_RESPONSE
MSG_TELEMETRY_BIN    = protocol.MSG_TELEMETRY_BIN

# Pre-computed for json.dumps (avoids tuple creation per call)
_JSON_SEPARATORS = (",", ":")


class BaseMaraClient(BinaryCommandsMixin):
    """
    Core async host-side MARA client with connection monitoring, reliable commands,
    and version handshake.
    """

    def __init__(
        self,
        transport: HasSendBytes,
        bus: Optional[EventBus] = None,
        heartbeat_interval_s: float = 0.2,
        connection_timeout_s: float = 1.0,
        command_timeout_s: float = 0.25,
        max_retries: int = 3,
        require_version_match: bool = True,
        handshake_timeout_s: float = 2.0,
        log_level: int = 20,  # logging.INFO
        log_dir: str = "logs",
        verbose: bool = True,
    ) -> None:
        self.transport = transport
        self.bus = bus or EventBus()
        self._verbose = verbose
        self._running = False
        self._seq = 0
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Version handshake
        self._require_version_match = require_version_match
        self._handshake_timeout_s = handshake_timeout_s
        self._version_verified = False
        self._firmware_version: Optional[str] = None
        self._protocol_version: Optional[int] = None
        self._schema_version: Optional[int] = None
        self._capabilities: Optional[int] = None
        self._features: Optional[list] = None
        self._board: Optional[str] = None
        self._platform_name: Optional[str] = None
        self._handshake_future: Optional[asyncio.Future] = None

        # Lazy logging (deferred initialization for startup speed)
        self._logs: Optional["MaraLogBundle"] = None
        self._log_config: Tuple[str, int] = (log_dir, log_level)

        # Connection monitor
        self.connection = ConnectionMonitor(
            timeout_s=connection_timeout_s,
            on_disconnect=self._on_disconnect,
            on_reconnect=self._on_reconnect,
        )

        # Reliable commander (uses lazy logs via property)
        # Handles both reliable (tracked) and streaming (fire-and-forget) commands
        self.commander = ReliableCommander(
            send_func=self._send_json_cmd_internal,
            send_binary_func=self._send_binary_cmd,
            timeout_s=command_timeout_s,
            max_retries=max_retries,
            on_event=lambda event, data: self._log_event(event, data),
        )

        self._heartbeat_interval_s = heartbeat_interval_s
        self._cached_identity: Optional[dict] = None

        # Transport will call _on_frame(body)
        self.transport.set_frame_handler(self._on_frame)

        # JSON-to-Binary encoder for efficient wire transmission
        self._init_binary_encoder()

    # ---------- Lazy logging ----------

    @property
    def logs(self) -> "MaraLogBundle":
        """Lazy-loaded log bundle for startup speed optimization."""
        if self._logs is None:
            from mara_host.logger.logger import MaraLogBundle
            log_dir, log_level = self._log_config
            self._logs = MaraLogBundle(
                name="mara_run",
                log_dir=log_dir,
                level=log_level,
                console=True,
            )
        return self._logs

    def _log_event(self, event: str, data: Dict[str, Any]) -> None:
        """Log event to lazy-loaded log bundle."""
        self.logs.events.write(event, **data)

    # ---------- Lifecycle ----------

    async def ensure_safe_baseline(self) -> None:
        """
        Best-effort: put robot into a known-safe state regardless of current state.
        Ignore errors because the robot may already be in that state.
        """
        for cmd, payload in [
            ("CMD_CLEAR_ESTOP", {}),   # <- first
            ("CMD_STOP", {}),
            ("CMD_DEACTIVATE", {}),
            ("CMD_DISARM", {}),
        ]:
            try:
                await self.send_reliable(cmd, payload, wait_for_ack=True)
            except Exception:
                pass

    async def start(self) -> None:
        """Start the transport, perform handshake, and start background tasks."""
        if self.transport is None:
            return

        start_fn = getattr(self.transport, "start", None)
        if start_fn is None:
            raise RuntimeError("Transport has no start() method")

        result = start_fn()
        if inspect.isawaitable(result):
            await result

        self._running = True

        # Perform version handshake before anything else
        if self._require_version_match:
            try:
                await self._perform_handshake()
            except Exception:
                self._running = False
                await self._stop_transport()
                raise

        # Start commander FIRST so send_reliable works well
        await self.commander.start_update_loop(interval_s=0.05)

        # NEW: normalize robot state before HIL tests call ARM/ACTIVATE
        # await self.ensure_safe_baseline()

        # Connection + heartbeat after baseline
        await self.connection.start_monitoring(interval_s=0.1)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if self._verbose:
            print("[MaraClient] Started")

    async def stop(self) -> None:
        """Stop the client and underlying transport (closes serial)."""
        self._running = False

        # 1) Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
            self._heartbeat_task = None

        # 2) STOP background senders/monitors BEFORE sending any more commands
        with contextlib.suppress(Exception):
            await self.connection.stop_monitoring()
        with contextlib.suppress(Exception):
            await self.commander.stop_update_loop()

        # 3) Clear anything queued/retrying
        with contextlib.suppress(Exception):
            self.commander.clear_pending()

        # 4) Optional: one best-effort STOP only (don’t DISARM/DEACTIVATE here)
        # This avoids “late disarm” affecting next test.
        with contextlib.suppress(Exception):
            await self.send("CMD_STOP", {})  # or whatever your non-reliable send is

        # 5) Close transport last
        await self._stop_transport()

        if self._verbose:
            print("[MaraClient] Stopped")


    async def _stop_transport(self) -> None:
        """Helper to stop transport."""
        if self.transport is None:
            return

        stop_fn = getattr(self.transport, "stop", None)
        if stop_fn is None:
            return

        result = stop_fn()
        if inspect.isawaitable(result):
            await result

    # ---------- Version Handshake ----------


    async def _perform_handshake(self) -> None:
        loop = asyncio.get_running_loop()
        if self._verbose:
            print(f"[MaraClient] Requesting identity/version (timeout={self._handshake_timeout_s}s)...")

        self._handshake_future = loop.create_future()
        # If identity arrived before handshake started, complete immediately
        if self._cached_identity is not None:
            if not self._handshake_future.done():
                self._handshake_future.set_result(self._cached_identity)
            self._cached_identity = None

        req_type = MSG_VERSION_REQUEST if MSG_VERSION_REQUEST is not None else MSG_WHOAMI

        # Make resend cadence scale down for short unit-test timeouts
        resend_every = max(0.05, min(0.5, self._handshake_timeout_s / 4))

        async def _resender() -> None:
            while self._running and self._handshake_future and not self._handshake_future.done():
                try:
                    await self._send_frame(req_type, b"")
                except Exception:
                    pass
                await asyncio.sleep(resend_every)

        resend_task = asyncio.create_task(_resender())

        try:
            result = await asyncio.wait_for(
                asyncio.shield(self._handshake_future),
                timeout=self._handshake_timeout_s,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Handshake timed out after {self._handshake_timeout_s}s. Is the firmware running?"
            )
        finally:
            resend_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await resend_task

        # Parse result
        self._firmware_version = result.get("firmware", "unknown")
        self._protocol_version = result.get("protocol", 0)
        self._schema_version = result.get("schema_version", 0)
        self._capabilities = result.get("capabilities", 0)
        self._features = result.get("features", [])
        self._board = result.get("board", "unknown")
        self._platform_name = result.get("name", "unknown")

        if self._verbose:
            print(f"[MaraClient] Firmware: {self._firmware_version}, "
                f"Protocol: {self._protocol_version}, "
                f"Schema: {self._schema_version}, "
                f"Board: {self._board}, "
                f"Name: {self._platform_name}, "
                f"Features: {self._features}")

        if self._protocol_version != PROTOCOL_VERSION:
            update_target = "firmware" if self._protocol_version < PROTOCOL_VERSION else "host"
            raise RuntimeError(
                f"Protocol version mismatch! Host expects {PROTOCOL_VERSION}, firmware has {self._protocol_version}. "
                f"Please update {update_target}."
            )

        self._version_verified = True
        if self._verbose:
            print("[MaraClient] Handshake OK")

    def _handle_version_response(self, payload: bytes) -> None:
        """Handle VERSION_RESPONSE from firmware."""
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as e:
            if self._verbose:
                print(f"[MaraClient] Failed to parse version response: {e}")
            data = {}
        
        self.bus.publish("version", data)
        
        if self._handshake_future and not self._handshake_future.done():
            self._handshake_future.set_result(data)

    # ---------- Connection callbacks ----------

    def _on_disconnect(self) -> None:
        self.commander.clear_pending()
        self.bus.publish("connection.lost", {})
        self.logs.events.write("connection.lost")

    def _on_reconnect(self) -> None:
        self.bus.publish("connection.restored", {})
        self.logs.events.write("connection.restored")

    # ---------- Heartbeat ----------

    async def _heartbeat_loop(self) -> None:
        last_snapshot = 0.0
        snapshot_every_s = 1.0

        while self._running:
            try:
                is_open = getattr(self.transport, "is_open", None)
                if callable(is_open) and not is_open():
                    await asyncio.sleep(self._heartbeat_interval_s)
                    continue

                await self._send_frame(MSG_HEARTBEAT, b"")

                now = time.monotonic()
                if (now - last_snapshot) >= snapshot_every_s:
                    self.logs.events.write("stats.snapshot", **self.get_stats())
                    last_snapshot = now

            except Exception as e:
                if self._running and self._verbose:
                    print(f"[MaraClient] Heartbeat error: {e}")

            await asyncio.sleep(self._heartbeat_interval_s)

    # ---------- Incoming data path ----------

    def _on_frame(self, body: bytes) -> None:
        """Called by the transport whenever a complete framed message arrives."""
        if not body:
            return

        # Update connection monitor early
        self.connection.on_message_received()

        # Fast path: check first byte directly (avoid slice creation)
        first_byte = body[0]
        if first_byte == 0x7B or first_byte == 0x5B:  # '{' or '['
            self._handle_json_payload(body)
            return

        msg_type = first_byte
        payload = body[1:] if len(body) > 1 else b""

        if msg_type == MSG_PONG:
            self.bus.publish("pong", {})
        elif msg_type == MSG_HEARTBEAT:
            self.bus.publish("heartbeat", {})
        elif msg_type == MSG_VERSION_RESPONSE:
            self._handle_version_response(payload)
        elif msg_type == MSG_CMD_JSON:
            self._handle_json_payload(payload)
        elif msg_type == MSG_TELEMETRY_BIN:
            telemetry_pkt = parse_telemetry_bin(payload)
            self.bus.publish("telemetry.binary", telemetry_pkt) 
        else:
            self.bus.publish(
                "raw_frame",
                {"msg_type": msg_type, "payload": payload},
            )

    def _handle_json_payload(self, payload: bytes) -> None:
        """Handle a JSON-encoded payload from the robot."""
        try:
            text = payload.decode("utf-8")
            obj = json.loads(text)
        except Exception as e:
            if self._verbose:
                print(f"[MaraClient] Failed to decode JSON payload: {e!r}")
            self.bus.publish("json_error", {"error": str(e), "raw": payload})
            return

        kind = obj.get("kind", "")

        # --- Identity handshake ---
        if kind == "identity":
            self.bus.publish("identity", obj)
            if self._handshake_future and not self._handshake_future.done():
                self._handshake_future.set_result(obj)
            else:
                self._cached_identity = obj
            return

        type_str = obj.get("type", "")
        cmd_str  = obj.get("cmd", "")

        # --- HELLO handshake ---
        if type_str == "HELLO":
            self.bus.publish("hello", obj)
            return

        # --- Telemetry ---
        if type_str == "TELEMETRY":
            self.bus.publish("telemetry.raw", obj)
            self.bus.publish("telemetry", obj)
            return

        # --- Command ACKs ---
        # FIX: MCU sends "cmd": "CMD_HEARTBEAT", not "CMD_HEARTBEAT_ACK"
        # Check for "ok" field and "src": "mcu" to identify ACKs
        if cmd_str and obj.get("src") == "mcu" and "ok" in obj:
            seq = obj.get("seq", -1)
            ok = obj.get("ok", False)
            error = obj.get("error")
            
            # Route to reliable commander
            self.commander.on_ack(seq, ok, error)
            
            # Also publish to bus for other listeners
            self.bus.publish(f"cmd.{cmd_str}", obj)
            
            # Publish state changes
            if "state" in obj:
                self.bus.publish("state.changed", {"state": obj["state"]})
            return

        # Fallback
        self.bus.publish("json", obj)
    # ---------- Outgoing commands ----------

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) & 0xFFFF
        return self._seq

    async def _send_frame(self, msg_type: int, payload: bytes = b"") -> None:
        """Encode and send a framed message via the transport."""
        frame = protocol.encode(msg_type, payload)
        await self.transport.send_bytes(frame)

    async def _send_json_cmd_internal(
        self,
        type_str: str,
        payload: Dict[str, Any],
        seq: Optional[int] = None,
    ) -> int:
        """
        Internal: send command JSON and return seq.

        If seq is provided, it is used as-is (for retries).
        Otherwise, a new sequence is allocated.
        """
        if seq is None:
            seq = self._next_seq()

        cmd_obj = {
            "kind": "cmd",
            "type": type_str,
            "seq": seq,
            **(payload or {}),
        }

        data = json.dumps(cmd_obj, separators=_JSON_SEPARATORS).encode("utf-8")
        await self._send_frame(MSG_CMD_JSON, data)
        return seq

    async def _send_binary_cmd(self, cmd_type: str, payload: Dict[str, Any]) -> None:
        """
        Internal: send command as binary (for streaming).

        Used by ReliableCommander for fire-and-forget binary commands.
        Lower latency and smaller wire size than JSON.
        """
        cmd = {"type": cmd_type, **payload}
        binary_payload = self._binary_encoder.encode(cmd)
        if binary_payload is not None:
            await self._send_frame(MSG_CMD_BIN, binary_payload)
        else:
            # Fall back to JSON if no binary encoding available
            await self._send_json_cmd_internal(cmd_type, payload)

    # ---------- Public API ----------

    async def send_ping(self) -> None:
        """Send a simple PING frame."""
        await self._send_frame(MSG_PING, b"")
    
    async def send_heartbeat(self) -> None:
        await self._send_frame(MSG_HEARTBEAT, b"")

    async def send_whoami(self) -> None:
        """Ask the MCU 'who are you?'."""
        await self._send_frame(MSG_WHOAMI, b"")

    async def send_json_cmd(self, type_str: str, payload: Optional[dict] = None) -> None:
        """
        Send a JSON command (fire and forget).
        For reliable delivery with ack, use send_reliable().
        """
        await self._send_json_cmd_internal(type_str, payload or {})

    async def send_reliable(
        self,
        type_str: str,
        payload: Optional[dict] = None,
        wait_for_ack: bool = True,
    ) -> tuple[bool, Optional[str]]:
        """
        Send a command with retry logic.
        
        Returns:
            (success, error_msg)
        """
        return await self.commander.send(type_str, payload, wait_for_ack)
    
    async def send_stream(
        self,
        cmd_type: str,
        payload: dict,
        request_ack: bool = False,
        binary: bool = False,
    ):
        """
        Streaming-friendly send. All commands flow through ReliableCommander.

        Args:
            cmd_type: Command type (e.g., "CMD_SET_VEL")
            payload: Command payload dict
            request_ack: If True, use reliable send with ACK tracking
            binary: If True, use binary encoding (lower latency for 50+ Hz)

        Returns:
            (success, error_msg) tuple
        """
        if request_ack:
            return await self.send_reliable(cmd_type, payload, wait_for_ack=True)

        # Fire-and-forget through commander (binary or JSON)
        await self.commander.send_fire_and_forget(cmd_type, payload, binary=binary)
        return True, None

    # ---------- Convenience methods ----------

    async def arm(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_ARM")
    
    async def disarm(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_DISARM")
    
    async def activate(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_ACTIVATE")
    
    async def deactivate(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_DEACTIVATE")
    
    async def estop(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_ESTOP")
    
    async def clear_estop(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_CLEAR_ESTOP")
    
    async def cmd_stop(self) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_STOP")
        
    async def set_vel(self, vx: float, omega: float) -> tuple[bool, Optional[str]]:
        return await self.send_reliable("CMD_SET_VEL", {"vx": vx, "omega": omega})

    # ---------- Properties ----------

    @property
    def is_connected(self) -> bool:
        return self.connection.connected
    
    @property
    def version_verified(self) -> bool:
        return self._version_verified
    
    @property
    def firmware_version(self) -> Optional[str]:
        return self._firmware_version
    
    @property
    def protocol_version(self) -> Optional[int]:
        return self._protocol_version

    @property
    def schema_version(self) -> Optional[int]:
        return self._schema_version

    @property
    def capabilities(self) -> Optional[int]:
        return self._capabilities

    @property
    def features(self) -> Optional[list]:
        return self._features

    @property
    def board(self) -> Optional[str]:
        return self._board
    
    @property
    def platform_name(self) -> Optional[str]:
        return self._platform_name
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "version_verified": self._version_verified,
            "firmware_version": self._firmware_version,
            "protocol_version": self._protocol_version,
            "schema_version": self._schema_version,
            "capabilities": self._capabilities,
            "features": self._features,
            "time_since_message": self.connection.time_since_last_message,
            **self.commander.stats(),
        }


class MaraClient(BaseMaraClient, RobotCommandsMixin):
    """
    Full async MARA (Modular Asynchronous Robotics Architecture) client:

      - Inherits all core transport / framing / telemetry behavior from
        BaseMaraClient.
      - Adds the autogenerated cmd_* JSON command helpers from RobotCommandsMixin.

    All module- or hardware-specific helpers (servo, GPIO, DC, IMU processing, etc.)
    should live in their respective HostModule classes, not here.
    """
    pass