# telemetry/host_module.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from mara_host.core.event_bus import EventBus
from mara_host.core.host_module import EventHostModule
from .parser import parse_telemetry
from .models import TelemetryPacket


class TelemetryHostModule(EventHostModule):
    """
    Parses raw telemetry and fans out to typed topics.

    Subscribes to: telemetry.raw (configurable)
    Publishes: telemetry.packet, telemetry.imu, telemetry.ultrasonic, etc.
    """

    module_name = "telemetry"

    def __init__(self, bus: EventBus, source_topic: str = "telemetry.raw") -> None:
        self._source_topic = source_topic
        self._latest: Optional[TelemetryPacket] = None
        super().__init__(bus)

    def subscriptions(self) -> List[str]:
        return [self._source_topic]

    def _get_handler(self, topic: str):
        # Override to map any source topic to _on_raw
        if topic == self._source_topic:
            return self._on_raw
        return super()._get_handler(topic)

    @property
    def latest(self) -> Optional[TelemetryPacket]:
        return self._latest

    def _on_raw(self, msg: Dict[str, Any]) -> None:
        if not isinstance(msg, dict):
            return
        if msg.get("type") != "TELEMETRY":
            return

        pkt = parse_telemetry(msg)
        self._latest = pkt

        # Full packet
        self._bus.publish("telemetry.packet", pkt)

        # Typed streams
        if pkt.imu is not None:
            self._bus.publish("telemetry.imu", pkt.imu)

        if pkt.ultrasonic is not None:
            self._bus.publish("telemetry.ultrasonic", pkt.ultrasonic)

        if pkt.lidar is not None:
            self._bus.publish("telemetry.lidar", pkt.lidar)

        if pkt.encoder0 is not None:
            self._bus.publish("telemetry.encoder0", pkt.encoder0)

        if pkt.stepper0 is not None:
            self._bus.publish("telemetry.stepper0", pkt.stepper0)

        if pkt.dc_motor0 is not None:
            self._bus.publish("telemetry.dc_motor0", pkt.dc_motor0)

        if pkt.sensor_health is not None:
            self._bus.publish("telemetry.sensor_health", pkt.sensor_health)
