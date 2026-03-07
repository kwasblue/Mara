from __future__ import annotations

import asyncio
import contextlib
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Union, Literal


Payload = Dict[str, Any]
StreamMode = Literal["latest", "queue"]

PayloadProvider = Union[
    Callable[[], Payload],                  # sync provider
    Callable[[], Awaitable[Payload]],        # async provider
]


@dataclass
class StreamSpec:
    name: str
    cmd: str
    rate_hz: float

    # Where does payload come from?
    provider: Optional[PayloadProvider] = None  # if None -> uses update()/mode storage
    mode: StreamMode = "latest"                 # "latest" or "queue"

    # Delivery semantics
    request_ack: bool = False                   # if True -> uses send_reliable (slower)
    max_in_flight: int = 1                      # only meaningful when request_ack=True

    # Gating
    require_connected: bool = True

    # Deadman / staleness behavior
    ttl_s: Optional[float] = None               # if set: stale payload disables sending
    on_ttl: Literal["skip", "stop_stream", "send_fallback_once"] = "skip"
    fallback_cmd: Optional[str] = None
    fallback_payload: Payload = field(default_factory=dict)

    # Internal state
    enabled: bool = False
    task: Optional[asyncio.Task] = None
    last_send_ts: float = 0.0
    last_update_ts: float = 0.0

    # Latest payload storage (mode="latest")
    latest_payload: Payload = field(default_factory=dict)

    # Queue storage (mode="queue")
    q: Optional[asyncio.Queue] = None

    # TTL fallback fire-once latch
    _ttl_fallback_fired: bool = False

    # Lazy copy flag - copy payload only when consumed, not on every update
    _payload_dirty: bool = False

    # Simple stats
    sent: int = 0
    errors: int = 0
    skipped_no_payload: int = 0
    skipped_stale: int = 0


class CommandStreamer:
    """
    Generic command streaming manager.

    Supports:
      - streaming any cmd at a fixed rate
      - payload from provider() or from update()
      - coalescing "latest" mode or "queue" mode
      - TTL/deadman and optional fallback command
      - optional ack-based sending (guarded by max_in_flight)

    Assumes robot has:
      - is_connected (bool) OR transport gating is done elsewhere
      - send_stream(cmd, payload, request_ack=False) -> (ok, err) or (True, None)
      - commander.pending_count() if you want to enforce max_in_flight
    """

    def __init__(
        self,
        robot: Any,
        *,
        default_rate_hz: float = 20.0,
        on_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        self.robot = robot
        self.default_rate_hz = float(default_rate_hz)
        self._streams: Dict[str, StreamSpec] = {}
        self._lock = asyncio.Lock()
        self._on_error = on_error

    # ---------------- Registration ----------------

    async def register(
        self,
        name: str,
        cmd: str,
        *,
        rate_hz: Optional[float] = None,
        provider: Optional[PayloadProvider] = None,
        mode: StreamMode = "latest",
        request_ack: bool = False,
        max_in_flight: int = 1,
        require_connected: bool = True,
        ttl_s: Optional[float] = None,
        on_ttl: Literal["skip", "stop_stream", "send_fallback_once"] = "skip",
        fallback_cmd: Optional[str] = None,
        fallback_payload: Optional[Payload] = None,
        queue_maxsize: int = 0,
        initial_payload: Optional[Payload] = None,
        autostart: bool = False,
    ) -> None:
        async with self._lock:
            if name in self._streams:
                raise ValueError(f"Stream {name!r} already exists")

            spec = StreamSpec(
                name=name,
                cmd=cmd,
                rate_hz=float(rate_hz or self.default_rate_hz),
                provider=provider,
                mode=mode,
                request_ack=bool(request_ack),
                max_in_flight=max(1, int(max_in_flight)),
                require_connected=bool(require_connected),
                ttl_s=None if ttl_s is None else float(ttl_s),
                on_ttl=on_ttl,
                fallback_cmd=fallback_cmd,
                fallback_payload=dict(fallback_payload or {}),
            )

            if spec.mode == "queue":
                spec.q = asyncio.Queue(maxsize=max(0, int(queue_maxsize)))

            if initial_payload is not None:
                spec.latest_payload = dict(initial_payload)
                spec.last_update_ts = time.monotonic()

            self._streams[name] = spec

        if autostart:
            await self.start(name)

    async def unregister(self, name: str) -> None:
        await self.stop(name)
        async with self._lock:
            self._streams.pop(name, None)

    def list_streams(self) -> list[str]:
        return sorted(self._streams.keys())

    def get_spec(self, name: str) -> StreamSpec:
        spec = self._streams.get(name)
        if not spec:
            raise KeyError(name)
        return spec

    # ---------------- Control ----------------

    async def start(self, name: str) -> None:
        spec = self._streams.get(name)
        if not spec:
            raise KeyError(f"No stream named {name!r}")
        if spec.enabled and spec.task and not spec.task.done():
            return
        spec.enabled = True
        spec._ttl_fallback_fired = False
        spec.task = asyncio.create_task(self._run_stream(spec))

    async def stop(self, name: str) -> None:
        spec = self._streams.get(name)
        if not spec:
            return
        spec.enabled = False
        if spec.task:
            spec.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await spec.task
            spec.task = None

    async def start_all(self) -> None:
        for name in self.list_streams():
            await self.start(name)

    async def stop_all(self) -> None:
        for name in self.list_streams():
            await self.stop(name)

    async def set_rate(self, name: str, rate_hz: float) -> None:
        spec = self.get_spec(name)
        spec.rate_hz = float(rate_hz)

    # ---------------- Data injection ----------------

    async def update(self, name: str, payload: Payload) -> None:
        """
        Update payload for non-provider streams.

        - mode="latest": overwrite latest payload (coalescing)
        - mode="queue": enqueue every payload (ordered)
        """
        spec = self.get_spec(name)
        spec.last_update_ts = time.monotonic()
        spec._ttl_fallback_fired = False  # fresh data resets TTL fallback latch

        if spec.provider is not None:
            # If you registered provider-based stream, update() isn't needed, but allow it.
            # Store reference directly - copy only when consumed
            spec.latest_payload = payload
            spec._payload_dirty = True
            return

        if spec.mode == "latest":
            # Store reference directly - avoid copy on every update (optimization)
            # Copy will happen in _get_payload() when consumed
            spec.latest_payload = payload
            spec._payload_dirty = True
            return

        # queue mode - must copy here since queue holds multiple items
        if spec.q is None:
            spec.q = asyncio.Queue()
        try:
            spec.q.put_nowait(dict(payload))
        except asyncio.QueueFull:
            # Drop oldest to make room (common for bursty producers)
            try:
                _ = spec.q.get_nowait()
            except Exception:
                pass
            with contextlib.suppress(asyncio.QueueFull):
                spec.q.put_nowait(dict(payload))

    # ---------------- Internals ----------------

    async def _get_provider_payload(self, provider: PayloadProvider, is_async: bool) -> Optional[Payload]:
        res = provider()
        if is_async:
            return dict(await res)
        return dict(res)

    def _is_connected(self, is_connected_attr: Any) -> bool:
        # Use cached attribute reference
        if is_connected_attr is None:
            return True
        try:
            return bool(is_connected_attr)
        except Exception:
            return True

    def _pending_count(self, commander: Any) -> int:
        if commander is None:
            return 0
        try:
            return int(commander.pending_count())
        except Exception:
            return 0

    def _ttl_expired(self, spec: StreamSpec) -> bool:
        if spec.ttl_s is None:
            return False
        if spec.last_update_ts <= 0:
            return False
        return (time.monotonic() - spec.last_update_ts) > spec.ttl_s

    async def _handle_ttl(self, spec: StreamSpec) -> None:
        spec.skipped_stale += 1

        if spec.on_ttl == "skip":
            return

        if spec.on_ttl == "stop_stream":
            await self.stop(spec.name)
            return

        if spec.on_ttl == "send_fallback_once":
            if spec._ttl_fallback_fired:
                return
            spec._ttl_fallback_fired = True

            if spec.fallback_cmd:
                try:
                    await self.robot.send_stream(spec.fallback_cmd, spec.fallback_payload, request_ack=False)
                except Exception:
                    # swallow fallback failure
                    pass
            return

    async def _get_payload(self, spec: StreamSpec, provider_is_async: bool = False) -> Optional[Payload]:
        # TTL/deadman only makes sense when payload is expected to be refreshed.
        if self._ttl_expired(spec):
            await self._handle_ttl(spec)
            return None

        # Provider-based stream
        if spec.provider is not None:
            p = await self._get_provider_payload(spec.provider, provider_is_async)
            # Provider counts as "fresh" data only if you WANT it to.
            # If you want TTL to apply to provider, you should update last_update_ts externally.
            return p

        # update()-based stream
        if spec.mode == "latest":
            if spec.last_update_ts == 0.0 and not spec.latest_payload:
                return None
            # Copy payload when consumed (lazy copy optimization)
            # This ensures caller can't mutate our stored payload
            result = dict(spec.latest_payload) if spec._payload_dirty else spec.latest_payload
            spec._payload_dirty = False
            return result

        # queue mode
        if spec.q is None:
            return None
        try:
            item = spec.q.get_nowait()
            return dict(item)
        except asyncio.QueueEmpty:
            return None

    async def _run_stream(self, spec: StreamSpec) -> None:
        next_t = time.monotonic()

        # Cache attribute lookups once at stream start (avoid getattr in hot loop)
        is_connected_attr = getattr(self.robot, "is_connected", None)
        commander = getattr(self.robot, "commander", None) if spec.request_ack else None

        # Cache whether provider is async (avoid inspect.isawaitable per call)
        provider_is_async = False
        if spec.provider is not None:
            # Check once if provider returns awaitable
            test_result = spec.provider()
            provider_is_async = inspect.isawaitable(test_result)
            if provider_is_async:
                # Consume the awaitable we just created
                try:
                    await test_result
                except Exception:
                    pass

        while spec.enabled:
            # recompute each loop so set_rate() takes effect immediately
            period = 1.0 / max(1e-6, float(spec.rate_hz))

            try:
                # Connection gating
                if spec.require_connected and not self._is_connected(is_connected_attr):
                    await asyncio.sleep(min(0.25, period))
                    continue

                # Ack gating: don't let streaming overwhelm pending reliable queue
                if spec.request_ack:
                    if self._pending_count(commander) >= spec.max_in_flight:
                        await asyncio.sleep(min(0.01, period))
                        continue

                payload = await self._get_payload(spec, provider_is_async)
                if payload is None:
                    spec.skipped_no_payload += 1
                else:
                    await self.robot.send_stream(spec.cmd, payload, request_ack=spec.request_ack)
                    spec.sent += 1
                    spec.last_send_ts = time.monotonic()

            except Exception as e:
                spec.errors += 1
                if self._on_error:
                    self._on_error(spec.name, e)

            # stable cadence
            next_t += period
            sleep_s = next_t - time.monotonic()
            if sleep_s < 0:
                next_t = time.monotonic()
                sleep_s = 0
            await asyncio.sleep(sleep_s)
