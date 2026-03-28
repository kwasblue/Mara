# mara_host/core/reliable_commander.py

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Dict, Any, Optional


class CommandStatus(Enum):
    PENDING = "pending"
    ACKED = "acked"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry behavior."""

    base_delay_s: float = 0.05  # Initial delay before first retry
    max_delay_s: float = 1.0  # Maximum delay cap
    jitter_factor: float = 0.1  # ±10% randomization to prevent thundering herd

    def calculate_backoff(self, retry_n: int) -> float:
        """
        Calculate backoff delay for given retry attempt.

        Uses exponential backoff with jitter:
            delay = min(base * 2^retry_n, max) ± jitter
        """
        delay = min(self.base_delay_s * (2**retry_n), self.max_delay_s)
        jitter = delay * self.jitter_factor * (random.random() * 2 - 1)
        return max(0.0, delay + jitter)


@dataclass
class PendingCommand:
    seq: int
    cmd_type: str
    payload: Dict[str, Any]
    first_sent_ns: int
    last_sent_ns: int
    retries: int = 0
    future: Optional[asyncio.Future] = None
    timeout_s: float = 0.25  # Per-command timeout (can override global default)
    next_retry_ns: int = 0  # When to attempt next retry (0 = immediate)

    @property
    def ack_ns(self) -> Optional[int]:
        """Time when ACK was received (set externally after ack)."""
        return getattr(self, "_ack_ns", None)

    @ack_ns.setter
    def ack_ns(self, value: int) -> None:
        self._ack_ns = value

    @property
    def latency_ms(self) -> float:
        """End-to-end latency from first send to ACK in milliseconds."""
        ack = self.ack_ns
        if ack is not None:
            return (ack - self.first_sent_ns) / 1e6
        return -1.0

    @property
    def last_hop_latency_ms(self) -> float:
        """Latency from last send (after retries) to ACK in milliseconds."""
        ack = self.ack_ns
        if ack is not None:
            return (ack - self.last_sent_ns) / 1e6
        return -1.0


class ReliableCommander:
    """
    Tracks pending commands and handles retries on timeout.

    All outgoing commands flow through this class, providing a single
    chokepoint for debugging and event logging.

    Supports two modes:
    - Reliable: Full tracking with ACK, retries, and timeout handling
    - Streaming: Fire-and-forget with optional binary encoding for low latency

    Features:
    - Per-command timeout configuration via command_defs
    - Exponential backoff with jitter on retries
    - Latency tracking (first-send-to-ack and last-hop)
    - Structured event emission for JSONL flight recorder

    Event emission for JSONL flight recorder:
        on_event("cmd.sent", {...})
        on_event("cmd.retry", {...})
        on_event("cmd.ack", {...})
        on_event("cmd.timeout", {...})
        on_event("cmd.cleared", {...})
    """

    # Maximum age for any pending command before forced eviction (prevents memory leaks)
    MAX_PENDING_AGE_S = 30.0

    def __init__(
        self,
        send_func: Callable[[str, Dict[str, Any], Optional[int]], Awaitable[int]],
        timeout_s: float = 0.25,
        max_retries: int = 3,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        send_binary_func: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        command_defs: Optional[Dict[str, Dict[str, Any]]] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        Args:
            send_func:
                Async function that sends JSON command and returns sequence number.
                Signature: async send_func(cmd_type, payload, seq_override) -> seq
            timeout_s: Default time to wait for ack before retry
            max_retries: Number of retries before giving up
            on_event: Optional callback for structured events (JSONL-friendly)
            send_binary_func:
                Optional async function for binary-encoded commands (streaming).
                Signature: async send_binary_func(cmd_type, payload) -> None
            command_defs:
                Optional dict of command definitions. If a command has a 'timeout_s'
                field, it overrides the default timeout for that command.
            retry_config:
                Optional RetryConfig for exponential backoff. If None, uses defaults.
        """
        self.send_func = send_func
        self.send_binary_func = send_binary_func
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self._on_event = on_event
        self._command_defs = command_defs or {}
        self._retry_config = retry_config or RetryConfig()

        self._pending: Dict[int, PendingCommand] = {}
        self._update_task: Optional[asyncio.Task] = None

        # Stats
        self.commands_sent = 0
        self.commands_sent_binary = 0
        self.acks_received = 0
        self.timeouts = 0
        self.retries = 0

        # Latency tracking
        self._latencies_ms: list[float] = []  # Recent latencies for percentile calculation
        self._max_latency_samples = 1000

    # ---------------- Helpers ----------------

    def _get_command_timeout(self, cmd_type: str) -> float:
        """
        Get timeout for a specific command type.

        Looks up command in command_defs for per-command timeout override.
        Falls back to global default timeout_s.
        """
        cmd_def = self._command_defs.get(cmd_type, {})
        return float(cmd_def.get("timeout_s", self.timeout_s))

    def _record_latency(self, latency_ms: float) -> None:
        """Record a latency sample for percentile tracking."""
        self._latencies_ms.append(latency_ms)
        if len(self._latencies_ms) > self._max_latency_samples:
            self._latencies_ms.pop(0)

    def get_latency_percentiles(self) -> Dict[str, float]:
        """
        Get latency percentiles (P50, P95, P99).

        Returns:
            Dict with keys 'p50', 'p95', 'p99', 'count', or empty if no samples.
        """
        if not self._latencies_ms:
            return {"p50": -1, "p95": -1, "p99": -1, "count": 0}

        sorted_latencies = sorted(self._latencies_ms)
        count = len(sorted_latencies)

        def percentile(p: float) -> float:
            idx = int(count * p / 100)
            return sorted_latencies[min(idx, count - 1)]

        return {
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
            "count": count,
        }

    # ---------------- Event emission ----------------

    def _emit(self, event: str, **data: Any) -> None:
        cb = self._on_event
        if cb is None:
            return
        try:
            cb({"event": event, **data})
        except Exception:
            # Never let logging break command delivery.
            pass

    # ---------------- Public API ----------------

    async def send(
        self,
        cmd_type: str,
        payload: Optional[Dict[str, Any]] = None,
        wait_for_ack: bool = True,
    ) -> tuple[bool, Optional[str]]:
        """
        Send a command and optionally wait for ack.

        Per-command timeout is looked up from command_defs if available,
        otherwise falls back to the global default timeout_s.

        Returns:
            (success, error_msg) if wait_for_ack else (True, None)
        """
        payload = payload or {}
        payload["wantAck"] = wait_for_ack
        sent_ns = time.monotonic_ns()
        seq = await self.send_func(cmd_type, payload, None)

        self.commands_sent += 1

        # Look up per-command timeout
        cmd_timeout = self._get_command_timeout(cmd_type)

        # Emit sent event regardless of ack mode
        self._emit(
            "cmd.sent",
            seq=seq,
            cmd_type=cmd_type,
            wait_for_ack=wait_for_ack,
            sent_ns=sent_ns,
            timeout_s=cmd_timeout,
            max_retries=self.max_retries,
            pending=len(self._pending),
        )

        if not wait_for_ack:
            return True, None

        loop = asyncio.get_event_loop()
        future: asyncio.Future[tuple[bool, Optional[str]]] = loop.create_future()

        self._pending[seq] = PendingCommand(
            seq=seq,
            cmd_type=cmd_type,
            payload=payload,
            first_sent_ns=sent_ns,
            last_sent_ns=sent_ns,
            future=future,
            timeout_s=cmd_timeout,  # Store per-command timeout
        )

        try:
            return await future
        except asyncio.CancelledError:
            self._pending.pop(seq, None)
            self._emit("cmd.cancelled", seq=seq, cmd_type=cmd_type)
            return False, "CANCELLED"

    async def send_fire_and_forget(
        self,
        cmd_type: str,
        payload: Optional[Dict[str, Any]] = None,
        binary: bool = False,
    ) -> Optional[int]:
        """
        Send without tracking. Use for streaming commands.

        Args:
            cmd_type: Command type (e.g., "CMD_SET_VEL")
            payload: Command payload dict
            binary: If True, use binary encoding (lower latency, smaller wire size)

        Returns:
            Sequence number (JSON path) or None (binary path)
        """
        sent_ns = time.monotonic_ns()

        if binary and self.send_binary_func is not None:
            # Binary path: lower latency, no sequence number
            await self.send_binary_func(cmd_type, payload or {})
            self.commands_sent += 1
            self.commands_sent_binary += 1
            self._emit(
                "cmd.sent",
                cmd_type=cmd_type,
                wait_for_ack=False,
                binary=True,
                sent_ns=sent_ns,
            )
            return None

        # JSON path: has sequence number
        if payload is None:
            payload = {"wantAck": False}
        elif "wantAck" not in payload:
            payload["wantAck"] = False
        seq = await self.send_func(cmd_type, payload, None)
        self.commands_sent += 1
        self._emit(
            "cmd.sent",
            seq=seq,
            cmd_type=cmd_type,
            wait_for_ack=False,
            binary=False,
            sent_ns=sent_ns,
        )
        return seq

    def on_ack(self, seq: int, ok: bool, error: Optional[str] = None) -> None:
        """Call when ack received from firmware."""
        ack_ns = time.monotonic_ns()
        cmd = self._pending.pop(seq, None)

        if cmd is None:
            self._emit("cmd.ack_orphan", seq=seq, ok=ok, error=error, ack_ns=ack_ns)
            return

        self.acks_received += 1

        # Set ack timestamp for latency tracking
        cmd.ack_ns = ack_ns
        first_latency_ms = cmd.latency_ms
        last_latency_ms = cmd.last_hop_latency_ms

        # Record latency for percentile tracking
        self._record_latency(first_latency_ms)

        self._emit(
            "cmd.ack",
            seq=cmd.seq,
            cmd_type=cmd.cmd_type,
            ok=ok,
            error=error,
            retries=cmd.retries,
            ack_ns=ack_ns,
            first_sent_ns=cmd.first_sent_ns,
            last_sent_ns=cmd.last_sent_ns,
            first_latency_ms=first_latency_ms,
            last_latency_ms=last_latency_ms,
            timeout_s=cmd.timeout_s,
            pending=len(self._pending),
        )

        if cmd.future and not cmd.future.done():
            cmd.future.set_result((ok, error))

    async def start_update_loop(self, interval_s: float = 0.05) -> None:
        """Start background task to handle retries."""
        if self._update_task is not None:
            return
        self._update_task = asyncio.create_task(self._update_loop(float(interval_s)))

    async def stop_update_loop(self) -> None:
        """Stop background task."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None


    # ---------------- Internals ----------------

    async def _update_loop(self, interval_s: float) -> None:
        while True:
            await self._update()
            await asyncio.sleep(interval_s)

    async def _update(self) -> None:
        """Handle retries and timeouts with exponential backoff."""
        now_ns = time.monotonic_ns()

        timed_out: list[int] = []
        to_retry: list[PendingCommand] = []
        stale: list[int] = []

        for seq, cmd in list(self._pending.items()):
            # Check for absolute max age (memory leak prevention)
            absolute_age_s = (now_ns - cmd.first_sent_ns) * 1e-9
            if absolute_age_s > self.MAX_PENDING_AGE_S:
                stale.append(seq)
                continue

            # Use per-command timeout
            age_s = (now_ns - cmd.last_sent_ns) * 1e-9
            if age_s > cmd.timeout_s:
                if cmd.retries < self.max_retries:
                    # Check if we've waited long enough for backoff
                    if cmd.next_retry_ns == 0 or now_ns >= cmd.next_retry_ns:
                        to_retry.append(cmd)
                else:
                    timed_out.append(seq)

        # Handle stale commands (forced eviction)
        for seq in stale:
            cmd = self._pending.pop(seq, None)
            if cmd is None:
                continue

            self._emit(
                "cmd.stale",
                seq=cmd.seq,
                cmd_type=cmd.cmd_type,
                age_s=(now_ns - cmd.first_sent_ns) * 1e-9,
            )

            if cmd.future and not cmd.future.done():
                cmd.future.set_result((False, "STALE"))

        # Handle retries with exponential backoff
        for cmd in to_retry:
            cmd.retries += 1
            cmd.last_sent_ns = now_ns
            self.retries += 1

            # Calculate next retry time with exponential backoff
            backoff_s = self._retry_config.calculate_backoff(cmd.retries)
            cmd.next_retry_ns = now_ns + int(backoff_s * 1e9)

            self._emit(
                "cmd.retry",
                seq=cmd.seq,
                cmd_type=cmd.cmd_type,
                retry_n=cmd.retries,
                sent_ns=now_ns,
                backoff_s=backoff_s,
                timeout_s=cmd.timeout_s,
                pending=len(self._pending),
            )

            # resend with SAME seq so the ACK matches the pending entry
            await self.send_func(cmd.cmd_type, cmd.payload, cmd.seq)

        # Handle final timeouts
        for seq in timed_out:
            cmd = self._pending.pop(seq, None)
            if cmd is None:
                continue

            self.timeouts += 1

            self._emit(
                "cmd.timeout",
                seq=cmd.seq,
                cmd_type=cmd.cmd_type,
                retries=cmd.retries,
                first_sent_ns=cmd.first_sent_ns,
                last_sent_ns=cmd.last_sent_ns,
                timeout_s=cmd.timeout_s,
                pending=len(self._pending),
            )

            if cmd.future and not cmd.future.done():
                cmd.future.set_result((False, "TIMEOUT"))
    
    def pending_count(self) -> int:
        return len(self._pending)
    
    def clear_pending(self) -> None:
        """Clear all pending commands (e.g., on disconnect)."""
        for cmd in self._pending.values():
            if cmd.future and not cmd.future.done():
                cmd.future.set_result((False, "CLEARED"))
        self._pending.clear()
    
    def stats(self) -> Dict[str, Any]:
        """
        Get commander statistics including latency percentiles.

        Returns:
            Dict with send/ack/timeout/retry counts and latency percentiles.
        """
        return {
            "commands_sent": self.commands_sent,
            "commands_sent_binary": self.commands_sent_binary,
            "acks_received": self.acks_received,
            "timeouts": self.timeouts,
            "retries": self.retries,
            "pending": self.pending_count(),
            "latency": self.get_latency_percentiles(),
        }