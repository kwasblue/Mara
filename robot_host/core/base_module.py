# robot_host/core/base_module.py
"""
Base module interface for Runtime composition.

Modules are pluggable components that extend robot functionality.
They integrate with the Runtime lifecycle and EventBus for clean composition.

Example:
    from robot_host.core.base_module import BaseModule

    class LoggingModule(BaseModule):
        name = "logging"

        def topics(self) -> list[str]:
            return ["telemetry.imu", "telemetry.encoder0"]

        async def start(self) -> None:
            self._file = open("telemetry.log", "w")

        async def stop(self) -> None:
            self._file.close()

        def on_telemetry_imu(self, data: dict) -> None:
            self._file.write(f"IMU: {data}\\n")

        def on_telemetry_encoder0(self, data: dict) -> None:
            self._file.write(f"ENC0: {data}\\n")

Usage with Runtime:
    runtime = Runtime(robot)
    runtime.add_module(LoggingModule())
    await runtime.run()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, List, Optional

if TYPE_CHECKING:
    from ..robot import Robot


class BaseModule(ABC):
    """
    Abstract base class for Runtime modules.

    Modules provide pluggable functionality that integrates with the
    Runtime lifecycle. Subclass this to create custom modules.

    Lifecycle:
        1. Module is added to Runtime via runtime.add_module(module)
        2. On runtime.start(): module.attach(robot) then module.start() called
        3. During runtime: topic callbacks invoked for subscribed topics
        4. On runtime.stop(): module.stop() called

    Topic Subscription:
        Override topics() to return a list of event topics to subscribe to.
        For each topic, implement a handler method named on_<topic_with_underscores>.

        Example:
            def topics(self) -> list[str]:
                return ["telemetry.imu"]

            def on_telemetry_imu(self, data: dict) -> None:
                print(f"IMU data: {data}")

    Attributes:
        name: Module name (used for logging and identification)
        robot: The Robot instance (set after attach())
    """

    # Override in subclass to set module name
    name: str = "base_module"

    def __init__(self) -> None:
        self._robot: Optional[Robot] = None
        self._subscriptions: List[Callable] = []

    @property
    def robot(self) -> Robot:
        """The Robot instance this module is attached to."""
        if self._robot is None:
            raise RuntimeError(f"Module '{self.name}' not attached to a robot")
        return self._robot

    def attach(self, robot: Robot) -> None:
        """
        Attach this module to a robot instance.

        Called by Runtime before start(). Sets up the robot reference
        and subscribes to declared topics.

        Args:
            robot: The Robot instance to attach to
        """
        self._robot = robot

        # Subscribe to declared topics
        for topic in self.topics():
            handler = self._get_handler_for_topic(topic)
            if handler:
                robot.on(topic, handler)
                self._subscriptions.append((topic, handler))

    def detach(self) -> None:
        """
        Detach this module from its robot.

        Called by Runtime after stop(). Unsubscribes from all topics.
        """
        if self._robot is not None:
            for topic, handler in self._subscriptions:
                self._robot.off(topic, handler)
        self._subscriptions.clear()
        self._robot = None

    def _get_handler_for_topic(self, topic: str) -> Optional[Callable]:
        """
        Get the handler method for a topic.

        Converts topic name to method name:
            "telemetry.imu" -> "on_telemetry_imu"
            "connection.lost" -> "on_connection_lost"
        """
        method_name = "on_" + topic.replace(".", "_").replace("-", "_")
        handler = getattr(self, method_name, None)
        if handler and callable(handler):
            return handler
        return None

    # --- Abstract/Override Methods ---

    def topics(self) -> List[str]:
        """
        Return list of event topics this module subscribes to.

        Override this method to declare topic subscriptions.
        For each topic, implement on_<topic_name> handler.

        Returns:
            List of topic strings (e.g., ["telemetry.imu", "connection.lost"])
        """
        return []

    async def start(self) -> None:
        """
        Called when the Runtime starts.

        Override to perform initialization (open files, start tasks, etc).
        The robot is already attached and connected at this point.
        """
        pass

    async def stop(self) -> None:
        """
        Called when the Runtime stops.

        Override to perform cleanup (close files, cancel tasks, etc).
        """
        pass

    async def on_tick(self, dt: float) -> None:
        """
        Called every Runtime tick.

        Override to perform periodic work. Only called if the module
        is registered for tick callbacks via Runtime.

        Args:
            dt: Time since last tick in seconds
        """
        pass

    def __repr__(self) -> str:
        attached = "attached" if self._robot else "detached"
        return f"{self.__class__.__name__}(name={self.name!r}, {attached})"
