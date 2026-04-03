# mara_host/core/client.py

from __future__ import annotations
import contextlib
import asyncio
import inspect
import time
from typing import Optional, Protocol, Callable, Dict, Any, Tuple

# Optimized JSON: Use orjson if available (2-3x faster than stdlib json)
try:
    import orjson
    _HAS_ORJSON = True
except ImportError:
    import json
    _HAS_ORJSON = False

from mara_host.core.event_bus import EventBus
from mara_host.core import protocol
from .coms.connection_monitor import ConnectionMonitor
from .coms.reliable_commander import ReliableCommander, RetryConfig
from mara_host.config.client_commands import RobotCommandsMixin
from mara_host.telemetry.binary_parser import parse_telemetry_bin
from mara_host.config.version import PROTOCOL_VERSION
from mara_host.tools.schema.error_codes import ErrorCode
from mara_host.tools.schema.commands import COMMANDS
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
MSG_ACK_BIN          = protocol.MSG_ACK_BIN
MSG_VERSION_REQUEST  = protocol.MSG_VERSION_REQUEST
MSG_VERSION_RESPONSE = protocol.MSG_VERSION_RESPONSE
MSG_TELEMETRY_BIN    = protocol.MSG_TELEMETRY_BIN

# Pre-computed for json.dumps (avoids tuple creation per call)
_JSON_SEPARATORS = (",", ":")

# Commands that need payload validation for safety
_VELOCITY_COMMANDS = frozenset({"CMD_SET_VEL", "CMD_SET_VELOCITY"})


def _validate_command_payload(cmd_type: str, payload: Dict[str, Any]) -> None:
    """
    Validate command payload before sending.

    Checks for NaN/Inf values in velocity commands to prevent
    dangerous MCU behavior. Binary encoder already validates these,
    but JSON commands skip that path.

    Raises:
        ValueError: If payload contains invalid values
    """
    import math

    if cmd_type in _VELOCITY_COMMANDS:
        vx = payload.get("vx", 0.0)
        omega = payload.get("omega", 0.0)
        if isinstance(vx, (int, float)):
            if math.isnan(vx) or math.isinf(vx):
                raise ValueError(f"Velocity vx cannot be NaN or Inf, got {vx}")
        if isinstance(omega, (int, float)):
            if math.isnan(omega) or math.isinf(omega):
                raise ValueError(f"Velocity omega cannot be NaN or Inf, got {omega}")


def _json_encode(obj: Dict[str, Any]) -> bytes:
    """Encode dict to JSON bytes. Uses orjson if available (2-3x faster)."""
    if _HAS_ORJSON:
        return orjson.dumps(obj)
    else:
        return json.dumps(obj, separators=_JSON_SEPARATORS).encode("utf-8")


def _json_decode(data: bytes) -> Dict[str, Any]:
    """Decode JSON bytes to dict. Uses orjson if available (faster, accepts bytes directly)."""
    if _HAS_ORJSON:
        return orjson.loads(data)
    else:
        return json.loads(data.decode("utf-8"))


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
        robot_name: Optional[str] = None,
    ) -> None:
        self.transport = transport
        self.bus = bus or EventBus()
        self._robot_name = robot_name
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
        # Lock to prevent race condition between handshake and cached identity
        # Using threading.Lock (not asyncio.Lock) because _handle_json_payload
        # is a sync callback that can't await an async lock.
        import threading
        self._handshake_lock = threading.Lock()

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
        # Pass COMMANDS dict for per-command timeout overrides
        self.commander = ReliableCommander(
            send_func=self._send_json_cmd_internal,
            send_binary_func=self._send_binary_cmd,
            timeout_s=command_timeout_s,
            max_retries=max_retries,
            on_event=lambda event, data: self._log_event(event, data),
            command_defs=COMMANDS,
            retry_config=RetryConfig(),  # Uses defaults: 50ms base, 1s max, 10% jitter
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

        # Connection + heartbeat
        await self.connection.start_monitoring(interval_s=0.1)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if self._verbose:
            print("[MaraClient] Started")

    async def stop(self) -> None:
        """Stop the client and underlying transport (closes serial)."""
        from mara_host.core.shutdown import shutdown_gracefully
        import logging

        _log = logging.getLogger(__name__)

        self._running = False

        # Define shutdown sequence with async wrappers
        async def cancel_heartbeat() -> None:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._heartbeat_task
                self._heartbeat_task = None

        async def clear_pending_async() -> None:
            await self.commander.clear_pending()

        async def send_stop_cmd() -> None:
            await self.send_json_cmd("CMD_STOP", {})

        components = [
            ("heartbeat", cancel_heartbeat),
            ("connection_monitor", self.connection.stop_monitoring),
            ("commander", self.commander.stop_update_loop),
            ("pending_commands", clear_pending_async),
            ("stop_command", send_stop_cmd),
            ("transport", self._stop_transport),
        ]

        result = await shutdown_gracefully(components)
        if result.errors:
            _log.warning(f"Shutdown had {len(result.errors)} errors")

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
        # Use lock to prevent race with _handle_json_payload setting _cached_identity
        with self._handshake_lock:
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
        import logging
        _log = logging.getLogger(__name__)

        try:
            data = _json_decode(payload)
        except Exception as e:
            _log.warning(
                "Failed to parse version response: %s (payload=%r)",
                e, payload[:100] if len(payload) > 100 else payload
            )
            if self._verbose:
                print(f"[MaraClient] Failed to parse version response: {e}")
            # Include parse error in result so handshake can report it
            data = {"_parse_error": str(e)}

        self.bus.publish("version", data)

        if self._handshake_future and not self._handshake_future.done():
            self._handshake_future.set_result(data)

    # ---------- Connection callbacks ----------

    def _on_disconnect(self) -> None:
        self.commander.clear_pending_sync()
        self.bus.publish("connection.lost", {})
        self.logs.events.write("connection.lost")

    def _on_reconnect(self) -> None:
        # Reset handshake state - MCU may have reset
        self._version_verified = False
        with self._handshake_lock:
            self._cached_identity = None

        # Clear stale in-flight commands (they won't get ACKs from reset MCU)
        self.commander.clear_pending_sync()

        # Schedule async re-handshake if required
        if self._require_version_match and self._running:
            # Publish reconnecting (not restored) - handshake not yet complete
            # Services should NOT send commands until connection.restored fires
            self.bus.publish("connection.reconnecting", {})
            self.logs.events.write("connection.reconnecting")

            task = asyncio.create_task(self._perform_handshake())
            # Attach error handler to prevent silent failures on version mismatch
            def _on_handshake_done(t: asyncio.Task) -> None:
                try:
                    t.result()
                    # Handshake succeeded - NOW publish connection.restored
                    self.bus.publish("connection.restored", {})
                    self.logs.events.write("connection.restored")
                except asyncio.CancelledError:
                    pass  # Expected on shutdown
                except Exception as e:
                    # Log handshake failure - connection may be in unverified state
                    import logging
                    logging.getLogger(__name__).error(
                        "Re-handshake after reconnect failed: %s. "
                        "Connection may be in unverified state.", e
                    )
                    self.bus.publish("handshake.failed", {"error": str(e)})
            task.add_done_callback(_on_handshake_done)
        else:
            # No handshake required - connection is immediately restored
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

        # Fast path: detect raw JSON by first byte (avoids slice creation).
        # This assumes the protocol will never use msg_type 0x7B ('{') or 0x5B ('[').
        # Current protocol msg_types are all <= 0x52, so this is safe.
        # If future msg_types approach these values, this heuristic must be revisited.
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
        elif msg_type == MSG_ACK_BIN:
            self._handle_binary_ack(payload)
        else:
            self.bus.publish(
                "raw_frame",
                {"msg_type": msg_type, "payload": payload},
            )

    def _handle_json_payload(self, payload: bytes) -> None:
        """Handle a JSON-encoded payload from the robot."""
        try:
            # Optimized: _json_decode uses orjson if available (accepts bytes directly)
            obj = _json_decode(payload)
        except Exception as e:
            if self._verbose:
                print(f"[MaraClient] Failed to decode JSON payload: {e!r}")
            self.bus.publish("json_error", {"error": str(e), "raw": payload})
            return

        kind = obj.get("kind", "")

        # --- Identity handshake ---
        if kind == "identity":
            self.bus.publish("identity", obj)
            # Use lock to prevent race with _perform_handshake reading _cached_identity
            with self._handshake_lock:
                if self._handshake_future and not self._handshake_future.done():
                    self._handshake_future.set_result(obj)
                else:
                    # Cache identity for later handshake
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
            error_code = obj.get("error_code")  # Structured error code (uint16)

            # Route to reliable commander
            self.commander.on_ack(seq, ok, error)

            # Enrich with parsed error code if present
            if error_code is not None:
                try:
                    obj["error_code_enum"] = ErrorCode(error_code)
                except ValueError:
                    pass  # Unknown error code, keep raw value

            # Also publish to bus for other listeners
            self.bus.publish(f"cmd.{cmd_str}", obj)

            # Publish state changes
            if "state" in obj:
                self.bus.publish("state.changed", {"state": obj["state"]})
            return

        # Fallback
        self.bus.publish("json", obj)

    def _handle_binary_ack(self, payload: bytes) -> None:
        """Handle a binary ACK frame from the robot."""
        try:
            seq, ok = protocol.decode_ack_bin(payload)
            self.commander.on_ack(seq, ok, None)
            self.bus.publish("cmd.ack_bin", {"seq": seq, "ok": ok})
        except ValueError as e:
            if self._verbose:
                print(f"[MaraClient] Failed to decode binary ACK: {e!r}")
            self.bus.publish("ack_bin_error", {"error": str(e), "raw": payload})

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
        # Validate payload for safety-critical commands
        _validate_command_payload(type_str, payload or {})

        if seq is None:
            seq = self._next_seq()

        cmd_obj = {
            "kind": "cmd",
            "type": type_str,
            "seq": seq,
            **(payload or {}),
        }

        # Optimized: _json_encode uses orjson if available (2-3x faster)
        data = _json_encode(cmd_obj)
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

    async def send_with_data(
        self,
        type_str: str,
        payload: Optional[dict] = None,
        timeout_s: float = 2.0,
    ) -> tuple[bool, Optional[str], Optional[dict]]:
        """
        Send a command and return the full response data.

        Unlike send_reliable which only returns (ok, error), this method
        captures the full response payload from the MCU.

        Returns:
            (success, error_msg, response_data)
        """
        import asyncio

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict] = loop.create_future()

        # Track send state to reject stale ACKs from prior commands
        send_started = False
        expected_seq: Optional[int] = None

        def on_response(msg: dict) -> None:
            nonlocal expected_seq
            if future.done():
                return

            # Reject ACKs that arrived before we started sending
            if not send_started:
                return

            # Verify sequence number matches if available
            if expected_seq is not None:
                ack_seq = msg.get("seq") if isinstance(msg, dict) else None
                if ack_seq is not None and ack_seq != expected_seq:
                    return  # Wrong sequence - stale ACK

            future.set_result(msg)

        # Subscribe to response on the bus
        topic = f"cmd.{type_str}"
        self.bus.subscribe(topic, on_response)

        try:
            # Get current seq before sending (will be incremented during send)
            pre_send_seq = self._seq
            send_started = True

            # Send the command
            ok, error = await self.send_reliable(type_str, payload)

            # After send, we know the seq that was used
            expected_seq = (pre_send_seq + 1) & 0xFFFF

            if not ok:
                return ok, error, None

            # Wait for bus response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=timeout_s)
                return response.get("ok", False), response.get("error"), response
            except asyncio.TimeoutError:
                return False, "Response timeout", None
        finally:
            self.bus.unsubscribe(topic, on_response)

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