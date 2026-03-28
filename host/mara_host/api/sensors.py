from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from .imu import IMU
from .ultrasonic import Ultrasonic
from .encoder import Encoder
from .sensor_base import TelemetrySensor
from mara_host.tools.schema.control_graph import SOURCE_DEFS


@dataclass
class SensorHealthStatus:
    name: str
    kind: str
    sensor_id: int = 0
    present: bool = False
    healthy: bool = False
    degraded: bool = False
    stale: bool = False
    required: bool = False
    fail_open: bool = True
    allow_missing: bool = True
    fallback: str = "none"
    stale_after_ms: Optional[int] = None
    detail: Optional[int] = None
    source: str = "config"
    last_update_monotonic_s: Optional[float] = None
    last_telemetry_ts_ms: Optional[int] = None

    def refresh_staleness(self, now_s: Optional[float] = None) -> bool:
        if self.stale_after_ms is None or self.last_update_monotonic_s is None:
            return self.stale
        now = time.monotonic() if now_s is None else now_s
        age_ms = max(0.0, (now - self.last_update_monotonic_s) * 1000.0)
        if age_ms >= self.stale_after_ms:
            self.stale = True
        return self.stale

    @property
    def available(self) -> bool:
        self.refresh_staleness()
        return self.present and self.healthy and not self.stale

    @property
    def usable(self) -> bool:
        if self.available:
            return True
        if not self.present:
            return self.allow_missing or self.fail_open
        if self.stale:
            return self.fail_open
        if not self.healthy or self.degraded:
            return self.fail_open
        return False

    @property
    def blocking(self) -> bool:
        return not self.usable and self.required

    def status_reason(self) -> str:
        self.refresh_staleness()
        if self.available:
            return "available"
        if not self.present:
            return "missing"
        if self.stale:
            return "stale"
        if not self.healthy:
            return "unhealthy"
        if self.degraded:
            return "degraded"
        return "unknown"


@dataclass
class SensorPolicyDecision:
    name: str
    kind: str
    sensor_id: int
    usable: bool
    blocking: bool
    reason: str
    fallback: str = "none"
    fail_open: bool = True


@dataclass
class SensorRequirementReport:
    ok: bool
    required_kinds: list[str]
    decisions: list[SensorPolicyDecision]

    @property
    def blocking(self) -> list[SensorPolicyDecision]:
        return [decision for decision in self.decisions if decision.blocking]


@dataclass
class SensorHandle:
    name: str
    kind: str
    sensor_id: int
    config: Any
    interface: Any
    health: SensorHealthStatus


class TelemetryMirrorSensor(TelemetrySensor[Any]):
    """Thin generic telemetry mirror for sensor types without a dedicated API yet."""

    def __init__(self, robot: "Robot", telemetry_topic: str, sensor_id: int = 0) -> None:
        self.telemetry_topic = telemetry_topic
        self._last_payload: Any = None
        super().__init__(robot, sensor_id=sensor_id, auto_subscribe=bool(telemetry_topic))

    def _filter_telemetry(self, data: Any) -> bool:
        if isinstance(data, dict) and "sensor_id" in data:
            return int(data.get("sensor_id", self._sensor_id)) == self._sensor_id
        sensor_id = getattr(data, "sensor_id", self._sensor_id)
        return int(sensor_id) == self._sensor_id

    def _parse_reading(self, data: Any) -> Any:
        self._last_payload = data
        return data

    @property
    def payload(self) -> Any:
        return self._last_payload


class SensorsFacade:
    """Thin Python-first sensor facade layered on existing config + sensor APIs."""

    _GENERIC_TOPICS = {
        "lidar": "telemetry.lidar",
        "tof": "telemetry.lidar",
        "distance": "telemetry.ultrasonic",
    }

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot
        self._handles: dict[str, SensorHandle] = {}
        self._topic_bound = False
        self._bind_from_config()
        self._bind_health_topic()

    def _bind_from_config(self) -> None:
        config = getattr(self._robot, "config", None)
        if config is None:
            return
        for sensor in config.iter_sensors(enabled_only=False):
            interface = self._build_interface(sensor.name, sensor.kind, sensor.sensor_id, sensor)
            degradation = sensor.degradation
            health = SensorHealthStatus(
                name=sensor.name,
                kind=sensor.kind,
                sensor_id=sensor.sensor_id,
                present=False,
                healthy=not degradation.required,
                degraded=bool(sensor.enabled and degradation.allow_missing),
                stale=False,
                required=degradation.required,
                fail_open=degradation.fail_open,
                allow_missing=degradation.allow_missing,
                fallback=degradation.fallback,
                stale_after_ms=degradation.stale_after_ms,
                source="config",
            )
            self._handles[sensor.name] = SensorHandle(
                name=sensor.name,
                kind=sensor.kind,
                sensor_id=sensor.sensor_id,
                config=sensor,
                interface=interface,
                health=health,
            )

    def _bind_health_topic(self) -> None:
        if self._topic_bound or getattr(self._robot, "_bus", None) is None:
            return
        self._robot.on("telemetry.sensor_health", self._on_sensor_health)
        self._topic_bound = True

    def _build_interface(self, name: str, kind: str, sensor_id: int, sensor_config: Any) -> Any:
        lowered = kind.lower()
        if lowered == "imu":
            return IMU(self._robot)
        if lowered == "ultrasonic":
            max_distance_cm = float(sensor_config.config.get("max_distance_cm", 400.0))
            return Ultrasonic(self._robot, sensor_id=sensor_id, max_distance_cm=max_distance_cm)
        if lowered == "encoder":
            return Encoder(
                self._robot,
                encoder_id=sensor_id,
                pin_a=int(sensor_config.pins.get("pin_a", 32)),
                pin_b=int(sensor_config.pins.get("pin_b", 33)),
                counts_per_rev=sensor_config.config.get("counts_per_rev"),
            )
        topic = getattr(sensor_config, "topic", None) or self._GENERIC_TOPICS.get(lowered)
        if isinstance(topic, str) and topic:
            return TelemetryMirrorSensor(self._robot, telemetry_topic=topic, sensor_id=sensor_id)
        return None

    def _on_sensor_health(self, telemetry: Any) -> None:
        sensors = getattr(telemetry, "sensors", None)
        if sensors is None:
            return
        now_s = time.monotonic()
        ts_ms = getattr(telemetry, "ts_ms", None)
        for entry in sensors:
            handle = self._match_entry(entry)
            if handle is None:
                continue
            handle.health.present = bool(entry.present)
            handle.health.healthy = bool(entry.healthy)
            handle.health.degraded = bool(entry.degraded)
            handle.health.stale = bool(entry.stale)
            handle.health.detail = entry.detail
            handle.health.source = "telemetry"
            handle.health.last_update_monotonic_s = now_s
            handle.health.last_telemetry_ts_ms = ts_ms
            handle.health.refresh_staleness(now_s)

    def _match_entry(self, entry: Any) -> Optional[SensorHandle]:
        for handle in self._handles.values():
            if handle.kind == entry.kind and handle.sensor_id == entry.sensor_id:
                return handle
        return None

    def _evaluate_handle(self, handle: SensorHandle) -> SensorPolicyDecision:
        health = handle.health
        health.refresh_staleness()
        return SensorPolicyDecision(
            name=handle.name,
            kind=handle.kind,
            sensor_id=handle.sensor_id,
            usable=health.usable,
            blocking=health.blocking,
            reason=health.status_reason(),
            fallback=health.fallback,
            fail_open=health.fail_open,
        )

    def names(self) -> list[str]:
        self._bind_health_topic()
        return sorted(self._handles)

    def get(self, name: str) -> Optional[SensorHandle]:
        self._bind_health_topic()
        return self._handles.get(name)

    def interface(self, name: str) -> Any:
        self._bind_health_topic()
        handle = self._handles.get(name)
        return None if handle is None else handle.interface

    def health(self, name: str) -> Optional[SensorHealthStatus]:
        self._bind_health_topic()
        handle = self._handles.get(name)
        if handle is None:
            return None
        handle.health.refresh_staleness()
        return handle.health

    def decision(self, name: str) -> Optional[SensorPolicyDecision]:
        self._bind_health_topic()
        handle = self._handles.get(name)
        return None if handle is None else self._evaluate_handle(handle)

    def by_kind(self, kind: str) -> list[SensorHandle]:
        lowered = kind.lower()
        return [handle for handle in self._handles.values() if handle.kind.lower() == lowered]

    def evaluate_required_kinds(self, required_kinds: list[str]) -> SensorRequirementReport:
        self._bind_health_topic()
        decisions: list[SensorPolicyDecision] = []
        seen: set[tuple[str, int]] = set()
        ok = True
        for kind in required_kinds:
            matches = self.by_kind(kind)
            if not matches:
                ok = False
                decisions.append(
                    SensorPolicyDecision(
                        name=f"<{kind}>",
                        kind=kind,
                        sensor_id=0,
                        usable=False,
                        blocking=True,
                        reason="unconfigured",
                        fallback="none",
                        fail_open=False,
                    )
                )
                continue
            for handle in matches:
                key = (handle.name, handle.sensor_id)
                if key in seen:
                    continue
                seen.add(key)
                decision = self._evaluate_handle(handle)
                decisions.append(decision)
                ok = ok and not decision.blocking
        return SensorRequirementReport(ok=ok, required_kinds=required_kinds, decisions=decisions)

    def evaluate_graph_requirements(self, graph: dict[str, Any]) -> SensorRequirementReport:
        required_kinds: list[str] = []
        for slot in graph.get("slots", []):
            source = slot.get("source", {})
            kind = source.get("type")
            spec = SOURCE_DEFS.get(kind)
            if spec is None:
                continue
            for requirement in spec.requires:
                if requirement not in required_kinds:
                    required_kinds.append(requirement)
        return self.evaluate_required_kinds(required_kinds)

    def snapshot(self) -> dict[str, SensorHandle]:
        self._bind_health_topic()
        for handle in self._handles.values():
            handle.health.refresh_staleness()
        return dict(self._handles)
