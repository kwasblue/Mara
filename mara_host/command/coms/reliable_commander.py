# mara_host/core/reliable_commander.py

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Dict, Any, Optional


class CommandStatus(Enum):
    PENDING = "pending"
    ACKED = "acked"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class PendingCommand:
    seq: int
    cmd_type: str
    payload: Dict[str, Any]
    first_sent_ns: int
    last_sent_ns: int
    retries: int = 0
    future: Optional[asyncio.Future] = None


class ReliableCommander:
    """
    Tracks pending commands and handles retries on timeout.

    Adds optional event emission so you can pipe events to your JSONL flight recorder:
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
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Args:
            send_func:
                Async function that sends command and returns sequence number.
                Signature: async send_func(cmd_type, payload, seq_override) -> seq
            timeout_s: Time to wait for ack before retry
            max_retries: Number of retries before giving up
            on_event: Optional callback for structured events (JSONL-friendly)
        """
        self.send_func = send_func
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self._on_event = on_event

        self._pending: Dict[int, PendingCommand] = {}
        self._update_task: Optional[asyncio.Task] = None

        # Stats
        self.commands_sent = 0
        self.acks_received = 0
        self.timeouts = 0
        self.retries = 0

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

        Returns:
            (success, error_msg) if wait_for_ack else (True, None)
        """
        payload = payload or {}
        payload["wantAck"] = wait_for_ack
        sent_ns = time.monotonic_ns()
        seq = await self.send_func(cmd_type, payload, None)

        self.commands_sent += 1

        # Emit sent event regardless of ack mode
        self._emit(
            "cmd.sent",
            seq=seq,
            cmd_type=cmd_type,
            wait_for_ack=wait_for_ack,
            sent_ns=sent_ns,
            timeout_s=self.timeout_s,
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
    ) -> int:
        """Send without tracking. Use for heartbeats etc."""
        payload = dict(payload or {})
        payload["wantAck"] = False
        sent_ns = time.monotonic_ns()
        seq = await self.send_func(cmd_type, payload, None)
        self.commands_sent += 1
        self._emit("cmd.sent", seq=seq, cmd_type=cmd_type, wait_for_ack=False, sent_ns=sent_ns)
        return seq

    def on_ack(self, seq: int, ok: bool, error: Optional[str] = None) -> None:
        """Call when ack received from firmware."""
        ack_ns = time.monotonic_ns()
        cmd = self._pending.pop(seq, None)

        if cmd is None:
            self._emit("cmd.ack_orphan", seq=seq, ok=ok, error=error, ack_ns=ack_ns)
            return

        self.acks_received += 1

        first_latency_ms = (ack_ns - cmd.first_sent_ns) * 1e-6
        last_latency_ms = (ack_ns - cmd.last_sent_ns) * 1e-6

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
        """Handle retries and timeouts."""
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

            age_s = (now_ns - cmd.last_sent_ns) * 1e-9
            if age_s > self.timeout_s:
                if cmd.retries < self.max_retries:
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

        # Handle retries
        for cmd in to_retry:
            cmd.retries += 1
            cmd.last_sent_ns = now_ns
            self.retries += 1

            self._emit(
                "cmd.retry",
                seq=cmd.seq,
                cmd_type=cmd.cmd_type,
                retry_n=cmd.retries,
                sent_ns=now_ns,
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
                timeout_s=self.timeout_s,
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
    
    def stats(self) -> Dict[str, int]:
        return {
            "commands_sent": self.commands_sent,
            "acks_received": self.acks_received,
            "timeouts": self.timeouts,
            "retries": self.retries,
            "pending": self.pending_count(),
        }