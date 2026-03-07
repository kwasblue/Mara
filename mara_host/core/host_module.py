# mara_host/core/host_module.py
"""
Abstract base classes for host-side modules.

Host modules are service classes that either:
1. Wrap robot commands (CommandHostModule)
2. Process events from the EventBus (EventHostModule)

These are different from Runtime modules (BaseModule) which have
lifecycle management and integrate with the Runtime loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient
    from mara_host.core.event_bus import EventBus


class CommandHostModule(ABC):
    """
    Abstract base class for command wrapper modules.

    Command modules wrap MaraClient methods to provide
    a cleaner API for specific hardware (servos, GPIO, motors, etc).

    Example:
        class ServoController(CommandHostModule):
            module_name = "servo"

            async def attach(self, servo_id: int, channel: int) -> None:
                await self._client.cmd_servo_attach(servo_id=servo_id, channel=channel)

            async def set_angle(self, servo_id: int, angle: float) -> None:
                await self._client.cmd_servo_set_angle(servo_id=servo_id, angle_deg=angle)
    """

    # Override in subclass to identify the module
    module_name: str = "command_module"

    def __init__(self, bus: "EventBus", client: "MaraClient") -> None:
        """
        Initialize the command module.

        Args:
            bus: EventBus for publishing events
            client: MaraClient for sending commands
        """
        self._bus = bus
        self._client = client

    @property
    def bus(self) -> "EventBus":
        """The EventBus instance."""
        return self._bus

    @property
    def client(self) -> "MaraClient":
        """The MaraClient instance."""
        return self._client

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(module_name={self.module_name!r})"


class EventHostModule(ABC):
    """
    Abstract base class for event processing modules.

    Event modules subscribe to EventBus topics and process/transform
    events (e.g., parsing raw telemetry, computing derived values).

    Subclasses must implement:
        - subscriptions(): Return list of topics to subscribe to

    Example:
        class TelemetryProcessor(EventHostModule):
            module_name = "telemetry"

            def subscriptions(self) -> List[str]:
                return ["telemetry.raw"]

            def _on_telemetry_raw(self, msg: dict) -> None:
                parsed = self._parse(msg)
                self._bus.publish("telemetry.parsed", parsed)
    """

    # Override in subclass to identify the module
    module_name: str = "event_module"

    def __init__(self, bus: "EventBus") -> None:
        """
        Initialize the event module and set up subscriptions.

        Args:
            bus: EventBus for subscribing and publishing
        """
        self._bus = bus
        self._setup_subscriptions()

    @property
    def bus(self) -> "EventBus":
        """The EventBus instance."""
        return self._bus

    @abstractmethod
    def subscriptions(self) -> List[str]:
        """
        Return list of topics this module subscribes to.

        For each topic, implement a handler method:
            topic "telemetry.raw" -> method "_on_telemetry_raw"
            topic "sensor.imu" -> method "_on_sensor_imu"
        """
        ...

    def _setup_subscriptions(self) -> None:
        """Subscribe to all declared topics."""
        for topic in self.subscriptions():
            handler = self._get_handler(topic)
            if handler:
                self._bus.subscribe(topic, handler)

    def _get_handler(self, topic: str):
        """Get handler method for a topic."""
        method_name = "_on_" + topic.replace(".", "_").replace("-", "_")
        return getattr(self, method_name, None)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(module_name={self.module_name!r})"
