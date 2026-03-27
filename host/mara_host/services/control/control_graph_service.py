from __future__ import annotations

from typing import Any

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService
from mara_host.tools.schema.control_graph.schema import normalize_graph_config, ControlGraphValidationError


class ControlGraphService(ConfigurableService[dict[str, Any], dict[str, Any]]):
    """Service for uploading and querying runtime control-graph configs."""

    def __init__(self, client):
        super().__init__(client)
        self._cached_graph: dict[str, Any] | None = None

    @staticmethod
    def _graph_matches_status(status_payload: dict[str, Any], graph: dict[str, Any]) -> bool:
        slots = status_payload.get("slots")
        expected_slots = graph.get("slots", [])
        if not status_payload.get("present"):
            return False
        if status_payload.get("schema_version") != graph.get("schema_version"):
            return False
        if status_payload.get("slot_count") != len(expected_slots):
            return False
        if not isinstance(slots, list) or len(slots) != len(expected_slots):
            return False
        for actual, expected in zip(slots, expected_slots):
            if actual.get("id") != expected.get("id"):
                return False
            if actual.get("enabled") != expected.get("enabled"):
                return False
        return True

    @property
    def cached_graph(self) -> dict[str, Any] | None:
        return self._cached_graph

    async def upload(self, graph: dict[str, Any]) -> ServiceResult:
        try:
            normalized = normalize_graph_config(graph)
        except ControlGraphValidationError as exc:
            return ServiceResult.failure(error=str(exc))

        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_UPLOAD",
            {"graph": normalized},
            error_message="Failed to upload control graph",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result

        self._cached_graph = normalized
        payload = dict(result.data or {})
        payload.setdefault("graph", normalized)
        return ServiceResult.success(data=payload)

    async def apply(self, graph: dict[str, Any], enable: bool = True) -> ServiceResult:
        upload_result = await self.upload(graph)
        if not upload_result.ok:
            return upload_result
        if not enable:
            return upload_result

        enable_result = await self.enable(True)
        if not enable_result.ok:
            return enable_result

        status_result = await self.status()
        if not status_result.ok:
            return status_result

        status_payload = dict(status_result.data or {})
        if not self._graph_matches_status(status_payload, self._cached_graph or {}):
            return ServiceResult.failure(
                error="Control graph apply did not persist on MCU; graph-status disagrees with upload"
            )

        payload = dict(upload_result.data or {})
        payload.update(enable_result.data or {})
        payload.update(status_payload)
        payload.setdefault("graph", self._cached_graph)
        payload.setdefault("applied", True)
        return ServiceResult.success(data=payload)

    async def clear(self) -> ServiceResult:
        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_CLEAR",
            {},
            error_message="Failed to clear control graph",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result
        self._cached_graph = None
        payload = dict(result.data or {})
        payload.setdefault("cleared", True)
        return ServiceResult.success(data=payload)

    async def enable(self, enable: bool = True) -> ServiceResult:
        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_ENABLE",
            {"enable": enable},
            error_message="Failed to change control-graph enable state",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result
        if self._cached_graph is not None:
            for slot in self._cached_graph.get("slots", []):
                slot["enabled"] = enable
        payload = dict(result.data or {})
        payload.setdefault("enabled", enable)
        if self._cached_graph is not None:
            payload.setdefault("graph", self._cached_graph)
        return ServiceResult.success(data=payload)

    async def disable(self) -> ServiceResult:
        return await self.enable(False)

    async def status(self) -> ServiceResult:
        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_STATUS",
            {},
            error_message="Failed to get control-graph status",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result

        payload = dict(result.data or {})
        if self._cached_graph is not None and "graph" not in payload:
            payload["graph"] = self._cached_graph
        return ServiceResult.success(data=payload)
