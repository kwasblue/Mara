from __future__ import annotations

import asyncio
import time
from typing import Any

from mara_host.core.result import ServiceResult
from mara_host.services.persistence.store import DiagnosticRecordStore


class McuDiagnosticsService:
    """Read and manage persisted MCU diagnostics in a Python-first way."""

    def __init__(
        self,
        client,
        diagnostics_store: DiagnosticRecordStore | None = None,
        *,
        ack_timeout_s: float = 0.5,
        retry_count: int = 3,
        retry_delay_s: float = 0.15,
        refresh_timeout_s: float = 1.5,
    ):
        self.client = client
        self._diagnostics_store = diagnostics_store
        self._latest_snapshot: dict[str, Any] | None = None
        self._waiters: list[asyncio.Future] = []
        self._ack_timeout_s = max(0.05, float(ack_timeout_s))
        self._retry_count = max(1, int(retry_count))
        self._retry_delay_s = max(0.0, float(retry_delay_s))
        self._refresh_timeout_s = max(0.1, float(refresh_timeout_s))
        self.client.bus.subscribe("telemetry", self._on_telemetry)

    @property
    def diagnostics_store(self) -> DiagnosticRecordStore | None:
        return self._diagnostics_store

    @property
    def latest_snapshot(self) -> dict[str, Any] | None:
        return None if self._latest_snapshot is None else dict(self._latest_snapshot)

    def close(self) -> None:
        self.client.bus.unsubscribe("telemetry", self._on_telemetry)
        for waiter in list(self._waiters):
            if not waiter.done():
                waiter.cancel()
        self._waiters.clear()

    @staticmethod
    def _normalize_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = {
            "captured_at": payload.get("captured_at", time.time()),
            "ready": bool(payload.get("ready", False)),
            "diagnostics": dict(payload.get("diagnostics") or {}),
        }
        config_mirror = payload.get("config_mirror")
        if isinstance(config_mirror, dict):
            snapshot["config_mirror"] = dict(config_mirror)
        return snapshot

    def _extract_snapshot(self, telemetry: dict[str, Any]) -> dict[str, Any] | None:
        persistence = telemetry.get("persistence")
        if not isinstance(persistence, dict):
            return None

        diagnostics = persistence.get("diagnostics")
        if not isinstance(diagnostics, dict):
            return None

        return self._normalize_snapshot_payload(
            {
                "captured_at": time.time(),
                "ready": persistence.get("ready", False),
                "diagnostics": diagnostics,
                "config_mirror": persistence.get("config_mirror"),
            }
        )

    def _record_snapshot(self, snapshot: dict[str, Any]) -> None:
        normalized = self._normalize_snapshot_payload(snapshot)
        self._latest_snapshot = normalized
        if self._diagnostics_store is not None:
            self._diagnostics_store.append("mcu_persistence", normalized)

        # Resolve all pending waiters with the new snapshot.
        # list() creates a copy to avoid mutation during iteration.
        # set_result() may synchronously trigger callbacks that append new
        # waiters, but those won't be in our copy and will be handled by
        # subsequent snapshots.
        for waiter in list(self._waiters):
            if waiter.done():
                continue
            waiter.set_result(dict(normalized))
        # Replace the list to clean up resolved futures. This is safe because
        # any new waiters added during set_result() callbacks are on the old
        # list reference which we're replacing entirely.
        self._waiters = [waiter for waiter in self._waiters if not waiter.done()]

    def _on_telemetry(self, telemetry: dict[str, Any]) -> None:
        if not isinstance(telemetry, dict):
            return
        snapshot = self._extract_snapshot(telemetry)
        if snapshot is not None:
            self._record_snapshot(snapshot)

    def read_cached(self) -> ServiceResult:
        if self._latest_snapshot is None:
            return ServiceResult.failure(error="No MCU persistence diagnostics have been observed yet")
        return ServiceResult.success(data=dict(self._latest_snapshot))

    async def read(self, *, force_refresh: bool = False, timeout_s: float = 1.5) -> ServiceResult:
        if not force_refresh and self._latest_snapshot is not None:
            return ServiceResult.success(data=dict(self._latest_snapshot))

        loop = asyncio.get_running_loop()
        waiter = loop.create_future()
        self._waiters.append(waiter)
        try:
            snapshot = await asyncio.wait_for(waiter, timeout=timeout_s)
            return ServiceResult.success(data=snapshot)
        except asyncio.TimeoutError:
            if self._latest_snapshot is not None:
                payload = dict(self._latest_snapshot)
                payload["stale"] = True
                return ServiceResult.success(data=payload)
            return ServiceResult.failure(error="Timed out waiting for MCU persistence telemetry")
        finally:
            if waiter in self._waiters:
                self._waiters.remove(waiter)

    async def query(self) -> ServiceResult:
        ack_result = await self._send_ack_query("CMD_MCU_DIAGNOSTICS_QUERY", "Failed to query MCU diagnostics")
        if not ack_result.ok:
            return ack_result

        raw_payload = dict(ack_result.data or {})
        snapshot = self._normalize_snapshot_payload(raw_payload)
        self._record_snapshot(snapshot)
        response = dict(snapshot)
        for key in ("fallback", "stale"):
            if key in raw_payload:
                response[key] = raw_payload[key]
        return ServiceResult.success(data=response)

    async def reset(self, *, clear_host_records: bool = False) -> ServiceResult:
        ack_result = await self._send_ack_query("CMD_MCU_DIAGNOSTICS_RESET", "Failed to reset MCU diagnostics")
        if not ack_result.ok:
            return ack_result

        payload = dict(ack_result.data or {})
        snapshot = payload.get("snapshot") if isinstance(payload.get("snapshot"), dict) else None
        if snapshot is not None:
            normalized = self._normalize_snapshot_payload(snapshot)
            self._record_snapshot(normalized)
            payload["snapshot"] = normalized
            payload.setdefault("diagnostics", normalized.get("diagnostics", {}))
            payload.setdefault("ready", normalized.get("ready", False))

        if clear_host_records:
            clear_result = self.clear_persisted_records()
            if not clear_result.ok:
                return clear_result
            payload["host_records_cleared"] = True

        return ServiceResult.success(data=payload)

    async def _send_ack_query(self, command: str, error_message: str, payload: dict[str, Any] | None = None) -> ServiceResult:
        # Subscribe to the command response topic. The client publishes JSON
        # responses to "cmd.{cmd_str}" where cmd_str is the command name from
        # the MCU response (see MaraClient._handle_json line 555).
        topic = f"cmd.{command}"
        last_error: str | None = None

        for attempt in range(1, self._retry_count + 1):
            loop = asyncio.get_running_loop()
            ack_future: asyncio.Future[Any] = loop.create_future()

            def _handler(data: Any) -> None:
                if not ack_future.done():
                    ack_future.set_result(data)

            self.client.bus.subscribe(topic, _handler)
            try:
                ok, error = await self.client.send_reliable(command, payload or {})
                if ok:
                    try:
                        ack_payload = await asyncio.wait_for(ack_future, timeout=self._ack_timeout_s)
                        return ServiceResult.success(data=ack_payload or {})
                    except asyncio.TimeoutError:
                        last_error = f"{error_message}: timed out waiting for ACK payload"
                else:
                    last_error = error or error_message
            finally:
                self.client.bus.unsubscribe(topic, _handler)

            if attempt < self._retry_count and self._retry_delay_s > 0:
                await asyncio.sleep(self._retry_delay_s * attempt)

        refresh_result = await self.read(force_refresh=True, timeout_s=self._refresh_timeout_s)
        if refresh_result.ok:
            payload = dict(refresh_result.data or {})
            payload.setdefault("fallback", "telemetry")
            payload.setdefault("stale", False)
            return ServiceResult.success(data=payload)

        detail = last_error or error_message
        if refresh_result.error:
            detail = f"{detail}; telemetry refresh failed: {refresh_result.error}"
        return ServiceResult.failure(error=detail)

    def clear_persisted_records(self) -> ServiceResult:
        if self._diagnostics_store is None:
            return ServiceResult.failure(
                error=(
                    "Host diagnostic persistence store is not configured in this context; "
                    "rerun without --clear-host-records or configure persistence.diagnostics"
                )
            )
        self._diagnostics_store.clear()
        return ServiceResult.success(data={"cleared": True, "scope": "host_store"})
