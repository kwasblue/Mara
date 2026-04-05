from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping

from mara_host.core.result import ServiceResult
from mara_host.services.control.service_base import ConfigurableService
from mara_host.services.persistence.store import ControlGraphStore
from mara_host.tools.schema.control_graph.schema import (
    ControlGraphConfig,
    ControlGraphValidationError,
    normalize_graph_model,
    validate_signal_references,
)


class ControlGraphService(ConfigurableService[dict[str, Any], dict[str, Any]]):
    """Service for uploading and querying runtime control-graph configs."""

    def __init__(
        self,
        client,
        sensor_policy_provider: Callable[[], Any] | None = None,
        persistence_store: ControlGraphStore | None = None,
    ):
        super().__init__(client)
        self._cached_graph_model: ControlGraphConfig | None = None
        self._cached_policy: dict[str, Any] | None = None
        self._sensor_policy_provider = sensor_policy_provider
        self._persistence_store = persistence_store

        # Protect cache from concurrent async access
        self._cache_lock = asyncio.Lock()

        # Subscribe to graph change events for cache invalidation
        self._subscriptions: list[tuple[str, Callable]] = []
        self._subscribe("ctrl_graph.changed", self._on_graph_changed)
        self._subscribe("ctrl_graph.cleared", self._on_graph_cleared)

    def _subscribe(self, topic: str, handler: Callable) -> None:
        """Track subscription for cleanup."""
        self.client.bus.subscribe(topic, handler)
        self._subscriptions.append((topic, handler))

    def _on_graph_changed(self, data: Any) -> None:
        """Handle graph change event from MCU - invalidate cache."""
        self.invalidate_cache()

    def _on_graph_cleared(self, data: Any) -> None:
        """Handle graph cleared event from MCU - invalidate cache."""
        self.invalidate_cache()

    def invalidate_cache(self) -> None:
        """
        Manually invalidate cached graph and policy.

        Note: This is a sync method for use from event handlers. For async
        contexts, cache writes are protected by _cache_lock in upload/clear/enable.
        """
        self._cached_graph_model = None
        self._cached_policy = None

    def close(self) -> None:
        """Clean up subscriptions."""
        for topic, handler in self._subscriptions:
            self.client.bus.unsubscribe(topic, handler)
        self._subscriptions.clear()

    @staticmethod
    def _graph_matches_status(status_payload: dict[str, Any], graph: Mapping[str, Any]) -> bool:
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

    @staticmethod
    def _serialize_policy_report(report: Any) -> dict[str, Any]:
        decisions: list[dict[str, Any]] = []
        for decision in getattr(report, "decisions", []) or []:
            if is_dataclass(decision):
                decisions.append(asdict(decision))
            elif isinstance(decision, dict):
                decisions.append(dict(decision))
            else:
                decisions.append(
                    {
                        "name": getattr(decision, "name", "<unknown>"),
                        "kind": getattr(decision, "kind", "<unknown>"),
                        "sensor_id": getattr(decision, "sensor_id", 0),
                        "usable": bool(getattr(decision, "usable", False)),
                        "blocking": bool(getattr(decision, "blocking", False)),
                        "reason": str(getattr(decision, "reason", "unknown")),
                        "fallback": str(getattr(decision, "fallback", "none")),
                        "fail_open": bool(getattr(decision, "fail_open", False)),
                    }
                )
        return {
            "ok": bool(getattr(report, "ok", True)),
            "required_kinds": list(getattr(report, "required_kinds", []) or []),
            "decisions": decisions,
            "blocking": [d for d in decisions if d.get("blocking")],
            "enforced": True,
        }

    def bind_sensor_policy_provider(self, provider: Callable[[], Any] | None) -> None:
        self._sensor_policy_provider = provider

    def _evaluate_graph_policy(self, graph: Mapping[str, Any]) -> dict[str, Any] | None:
        if self._sensor_policy_provider is None:
            self._cached_policy = None
            return None
        facade = self._sensor_policy_provider()
        if facade is None or not hasattr(facade, "evaluate_graph_requirements"):
            self._cached_policy = None
            return None
        report = facade.evaluate_graph_requirements(graph)
        policy = self._serialize_policy_report(report)
        self._cached_policy = policy
        return policy

    @property
    def cached_graph_model(self) -> ControlGraphConfig | None:
        return self._cached_graph_model

    @property
    def cached_graph(self) -> dict[str, Any] | None:
        return self._cached_graph_model.to_dict() if self._cached_graph_model is not None else None

    @property
    def cached_policy(self) -> dict[str, Any] | None:
        return self._cached_policy

    @property
    def persistence_store(self) -> ControlGraphStore | None:
        return self._persistence_store

    @staticmethod
    def _graph_for_safe_restore(graph: ControlGraphConfig) -> ControlGraphConfig:
        return graph.with_enabled(False)

    async def upload(
        self,
        graph: dict[str, Any] | ControlGraphConfig,
        commit: bool = True,
        mode: str = "replace",
        validate_signals: bool = False,
        external_signals: set[int] | None = None,
    ) -> ServiceResult:
        """
        Upload a control graph to the MCU.

        Args:
            graph: The control graph configuration to upload.
            commit: If True (default), immediately activate the graph.
                   If False, stage as pending for two-phase commit.
                   Use commit() method to activate a pending graph.
            mode: Upload mode:
                  - "replace" (default): Clear all, upload new graph
                  - "merge": Preserve runtime state for unchanged slots.
                    Slots with matching ID and identical config keep their
                    integrator values, filter states, encoder state, etc.
            validate_signals: If True, validate that all signal reads reference
                             signals that are written by the graph or listed
                             in external_signals.
            external_signals: Signal IDs that are written by host code (not by
                             the graph itself). Only used if validate_signals=True.

        Returns:
            ServiceResult with upload status.
            If commit=False, includes 'token' and 'hash' for later commit.

        Example:
            # Re-upload same graph, preserving filter/integrator state
            await service.upload(graph, mode="merge")
        """
        try:
            normalized_model = normalize_graph_model(graph)
        except ControlGraphValidationError as exc:
            return ServiceResult.failure(error=str(exc))

        # Optional signal reference validation
        if validate_signals:
            signal_errors = validate_signal_references(normalized_model, external_signals)
            if signal_errors:
                return ServiceResult.failure(
                    error="Signal reference validation failed",
                    data={"signal_errors": signal_errors},
                )

        normalized = normalized_model.to_dict()
        policy = self._evaluate_graph_policy(normalized)

        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_UPLOAD",
            {"graph": normalized, "commit": commit, "mode": mode},
            error_message="Failed to upload control graph",
            ack_timeout_s=5.0,  # Graph upload needs more time for MCU processing
        )
        if not result.ok:
            return result

        # Only update cache if committed immediately
        if commit:
            async with self._cache_lock:
                self._cached_graph_model = normalized_model

            # Persist to store - catch validation errors to avoid state divergence
            persistence_error = None
            if self._persistence_store is not None:
                try:
                    self._persistence_store.save_graph(normalized_model)
                except Exception as e:
                    persistence_error = str(e)
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Failed to persist control graph (MCU has it): {e}"
                    )

            payload = dict(result.data or {})
            if persistence_error:
                payload["persistence_warning"] = persistence_error
        else:
            # Pending upload - don't update cache yet
            payload = dict(result.data or {})
            payload["pending"] = True

        payload.setdefault("graph", normalized)
        if policy is not None:
            payload["policy"] = policy
        return ServiceResult.success(data=payload)

    async def commit(self, token: int) -> ServiceResult:
        """
        Commit a pending control graph upload.

        Args:
            token: The token returned from upload(commit=False).

        Returns:
            ServiceResult with commit status.
        """
        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_COMMIT",
            {"token": token},
            error_message="Failed to commit control graph",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result

        # Update cache now that graph is committed
        # Note: We don't have the model cached from pending upload,
        # so the caller should re-query status if they need the full graph
        return ServiceResult.success(data=dict(result.data or {}))

    async def _get_robot_mode(self) -> str:
        """Get current robot mode (IDLE/ARMED/ACTIVE/ESTOP)."""
        try:
            ok, error, data = await self.client.send_with_data("CMD_GET_ROBOT_STATE", {})
            if ok and data:
                return data.get("mode", "UNKNOWN")
        except Exception:
            pass
        return "UNKNOWN"

    async def _ensure_armed(self) -> ServiceResult:
        """Ensure robot is in ARMED state, arming if necessary."""
        mode = await self._get_robot_mode()
        if mode == "ARMED":
            return ServiceResult.success(data={"mode": mode, "action": "already_armed"})

        if mode == "ACTIVE":
            # Deactivate first, then we're armed
            ok, error = await self.client.send_reliable("CMD_DEACTIVATE")
            if not ok:
                return ServiceResult.failure(error=f"Failed to deactivate: {error}")
            return ServiceResult.success(data={"mode": "ARMED", "action": "deactivated"})

        if mode in ("IDLE", "UNKNOWN"):
            ok, error = await self.client.send_reliable("CMD_ARM")
            if not ok:
                return ServiceResult.failure(error=f"Failed to arm: {error}")
            return ServiceResult.success(data={"mode": "ARMED", "action": "armed"})

        if mode == "ESTOP":
            return ServiceResult.failure(error="Robot is in ESTOP state - clear estop first")

        return ServiceResult.failure(error=f"Unknown robot mode: {mode}")

    async def apply(
        self,
        graph: dict[str, Any] | ControlGraphConfig,
        enable: bool = True,
        auto_clear: bool = True,
        ensure_armed: bool = True,
    ) -> ServiceResult:
        """
        Upload and optionally enable a control graph with automatic state management.

        Args:
            graph: The control graph configuration to upload
            enable: If True (default), enable the graph after upload
            auto_clear: If True (default), clear any existing graph first to prevent
                       busy-state timeouts when re-uploading
            ensure_armed: If True (default), automatically arm the robot if not armed

        Returns:
            ServiceResult with upload status, graph config, and policy info
        """
        # Pre-check policy BEFORE upload to avoid uploading a graph we can't enable
        if enable:
            try:
                normalized_model = normalize_graph_model(graph)
                normalized = normalized_model.to_dict()
                policy = self._evaluate_graph_policy(normalized)
                if policy is not None and policy["blocking"]:
                    return ServiceResult.failure(
                        error="Control graph blocked by sensor policy",
                        data={"graph": normalized, "policy": policy, "uploaded": False},
                    )
            except ControlGraphValidationError as exc:
                return ServiceResult.failure(error=str(exc))

        # Step 1: Ensure robot is armed
        if ensure_armed:
            arm_result = await self._ensure_armed()
            if not arm_result.ok:
                return ServiceResult.failure(
                    error=f"Cannot upload graph: {arm_result.error}"
                )

        # Step 2: Clear existing graph to prevent busy-state issues
        if auto_clear:
            await self.clear()
            # Re-arm after clear (clear may affect state on some firmware versions)
            if ensure_armed:
                await self._ensure_armed()

        # Step 3: Upload the graph
        upload_result = await self.upload(graph)
        if not upload_result.ok:
            return upload_result
        if not enable:
            return upload_result

        # Step 4: Enable the graph
        enable_result = await self.enable(True)
        if not enable_result.ok:
            return enable_result

        # Step 5: Verify upload succeeded
        status_result = await self.status()
        if not status_result.ok:
            return status_result

        status_payload = dict(status_result.data or {})
        if not self._graph_matches_status(status_payload, self.cached_graph or {}):
            return ServiceResult.failure(
                error="Control graph apply did not persist on MCU; graph-status disagrees with upload"
            )

        payload = dict(upload_result.data or {})
        payload.update(enable_result.data or {})
        payload.update(status_payload)
        payload.setdefault("graph", self.cached_graph)
        payload.setdefault("applied", True)
        if self._cached_policy is not None:
            payload["policy"] = self._cached_policy
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
        # Update cache under lock for thread safety
        async with self._cache_lock:
            self._cached_graph_model = None
            self._cached_policy = None
        if self._persistence_store is not None:
            self._persistence_store.clear()
        payload = dict(result.data or {})
        payload.setdefault("cleared", True)
        return ServiceResult.success(data=payload)

    async def enable(self, enable: bool = True) -> ServiceResult:
        if enable and self.cached_graph is not None:
            policy = self._evaluate_graph_policy(self.cached_graph)
            if policy is not None and policy["blocking"]:
                return ServiceResult.failure(
                    error="Control graph enable blocked by sensor policy",
                    data={"graph": self.cached_graph, "policy": policy},
                )

        result = await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_ENABLE",
            {"enable": enable},
            error_message="Failed to change control-graph enable state",
            ack_timeout_s=0.25,
        )
        if not result.ok:
            return result
        # Update cache under lock for thread safety
        async with self._cache_lock:
            if self._cached_graph_model is not None:
                self._cached_graph_model = self._cached_graph_model.with_enabled(enable)
        payload = dict(result.data or {})
        payload.setdefault("enabled", enable)
        if self.cached_graph is not None:
            payload.setdefault("graph", self.cached_graph)
        if self._cached_policy is not None:
            payload["policy"] = self._cached_policy
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
        if self.cached_graph is not None and "graph" not in payload:
            payload["graph"] = self.cached_graph
        if self.cached_graph is not None:
            policy = self._evaluate_graph_policy(self.cached_graph)
            if policy is not None:
                payload["policy"] = policy
        return ServiceResult.success(data=payload)

    async def restore_from_persistence(self) -> ServiceResult:
        if self._persistence_store is None:
            return ServiceResult.failure(error="Control graph persistence store is not configured")

        graph = self._persistence_store.load_graph_model()
        if graph is None:
            return ServiceResult.failure(error="No persisted control graph found")

        safe_graph = self._graph_for_safe_restore(graph)
        upload_result = await self.upload(safe_graph)
        if not upload_result.ok:
            return upload_result

        disable_result = await self.enable(False)
        if not disable_result.ok:
            return disable_result

        payload = dict(upload_result.data or {})
        payload.update(disable_result.data or {})
        payload["restored"] = True
        payload["restored_safely"] = True
        payload["graph"] = safe_graph.to_dict()
        payload["restored_from_enabled_state"] = any(slot.enabled for slot in graph.slots)
        return ServiceResult.success(data=payload)

    async def set_debug_slot(self, slot_id: str | None) -> ServiceResult:
        """
        Enable debug streaming for a single slot to see intermediate transform values.

        Args:
            slot_id: The slot ID to enable debug for, or None/empty string to disable.

        Returns:
            ServiceResult with debug_enabled and slot_id fields.

        Only one slot can be in debug mode at a time due to bandwidth constraints.
        Debug values will appear in telemetry as an array of floats representing:
        [source_value, transform_1_output, transform_2_output, ..., final_output]
        """
        return await self._send_reliable_with_ack_payload(
            "CMD_CTRL_GRAPH_DEBUG",
            {"slot_id": slot_id or ""},
            error_message="Failed to set debug slot",
            ack_timeout_s=0.25,
        )

    async def get_slot_health(self) -> ServiceResult:
        """
        Get health status for all slots in the control graph.

        Returns:
            ServiceResult with slots array containing health info per slot:
            - id: slot identifier
            - healthy: whether slot is running at expected rate
            - rate_hz: configured rate
            - actual_hz: measured rate
            - actual_period_us: measured period in microseconds
            - min_period_us: minimum observed period
            - max_period_us: maximum observed period
            - error: error string if slot has an error
        """
        result = await self.status()
        if not result.ok:
            return result

        slots = result.data.get("slots", [])
        health_info: list[dict[str, Any]] = []
        unhealthy_slots: list[str] = []

        for slot in slots:
            slot_health = {
                "id": slot.get("id"),
                "healthy": slot.get("healthy", True),
                "rate_hz": slot.get("rate_hz", 0),
                "actual_hz": slot.get("actual_hz", 0),
                "actual_period_us": slot.get("actual_period_us", 0),
                "min_period_us": slot.get("min_period_us", 0),
                "max_period_us": slot.get("max_period_us", 0),
                "error": slot.get("error"),
            }
            health_info.append(slot_health)

            if not slot_health["healthy"]:
                unhealthy_slots.append(slot_health["id"])

        # Emit event if any slots are unhealthy
        if unhealthy_slots:
            self.client.bus.emit("ctrl_graph.unhealthy_slots", {
                "slot_ids": unhealthy_slots,
                "slots": [s for s in health_info if not s["healthy"]],
            })

        return ServiceResult.success(data={
            "all_healthy": len(unhealthy_slots) == 0,
            "unhealthy_count": len(unhealthy_slots),
            "slots": health_info,
        })
