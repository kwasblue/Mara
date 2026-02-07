# robot_host/runtime/runtime.py
"""
Canonical runtime loop for robot applications.

Provides a structured way to run robot control loops with:
- Configurable tick rate
- Module lifecycle management
- Telemetry callbacks
- Graceful start/stop

Example:
    from robot_host import Robot
    from robot_host.runtime import Runtime

    async def main():
        async with Robot("/dev/ttyUSB0") as robot:
            runtime = Runtime(robot, tick_hz=50.0)

            @runtime.on_tick
            async def control_loop(dt: float):
                # Called every tick
                await robot.motion.set_velocity(0.1, 0.0)

            @runtime.on_telemetry
            def handle_telemetry(data):
                print(f"IMU: {data.get('imu')}")

            await runtime.run()  # Runs until stopped
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, Optional

if TYPE_CHECKING:
    from ..robot import Robot


# Type aliases for callbacks
TickCallback = Callable[[float], Coroutine[Any, Any, None]]  # async def(dt) -> None
TelemetryCallback = Callable[[dict], None]  # def(data) -> None
LifecycleCallback = Callable[[], Coroutine[Any, Any, None]]  # async def() -> None


@dataclass
class RuntimeConfig:
    """Configuration for the runtime loop."""
    tick_hz: float = 50.0
    telemetry_topics: List[str] = field(default_factory=lambda: ["telemetry"])
    auto_arm: bool = False
    stop_on_error: bool = True


class Runtime:
    """
    Canonical runtime loop for robot applications.

    Provides a structured, extensible way to run robot control loops.
    This is the "blessed" way to build robot applications on robot_host.

    Args:
        robot: Connected Robot instance
        tick_hz: Control loop frequency (default: 50.0 Hz)
        auto_arm: Automatically arm robot on start (default: False)

    Example:
        runtime = Runtime(robot, tick_hz=50.0)

        @runtime.on_tick
        async def control(dt):
            await robot.motion.set_velocity(0.1, 0.0)

        @runtime.on_start
        async def setup():
            await robot.arm()

        @runtime.on_stop
        async def cleanup():
            await robot.disarm()

        await runtime.run()
    """

    def __init__(
        self,
        robot: Robot,
        tick_hz: float = 50.0,
        auto_arm: bool = False,
    ) -> None:
        self._robot = robot
        self._config = RuntimeConfig(tick_hz=tick_hz, auto_arm=auto_arm)
        self._tick_period = 1.0 / tick_hz

        # Callbacks
        self._tick_callbacks: List[TickCallback] = []
        self._telemetry_callbacks: List[TelemetryCallback] = []
        self._start_callbacks: List[LifecycleCallback] = []
        self._stop_callbacks: List[LifecycleCallback] = []

        # State
        self._running = False
        self._stop_event: Optional[asyncio.Event] = None
        self._tick_count = 0
        self._start_time: Optional[float] = None

    # --- Properties ---

    @property
    def robot(self) -> Robot:
        """The Robot instance this runtime is managing."""
        return self._robot

    @property
    def config(self) -> RuntimeConfig:
        """Runtime configuration."""
        return self._config

    @property
    def is_running(self) -> bool:
        """Whether the runtime loop is currently running."""
        return self._running

    @property
    def tick_count(self) -> int:
        """Number of ticks since start."""
        return self._tick_count

    @property
    def elapsed_time(self) -> float:
        """Elapsed time in seconds since start."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    # --- Callback Registration ---

    def on_tick(self, callback: TickCallback) -> TickCallback:
        """
        Register a callback to be called every tick.

        The callback receives dt (time since last tick in seconds).
        Can be used as a decorator.

        Example:
            @runtime.on_tick
            async def control(dt: float):
                await robot.motion.set_velocity(0.1, 0.0)
        """
        self._tick_callbacks.append(callback)
        return callback

    def on_telemetry(self, callback: TelemetryCallback) -> TelemetryCallback:
        """
        Register a callback for telemetry events.

        The callback receives the telemetry data dict.
        Can be used as a decorator.

        Example:
            @runtime.on_telemetry
            def handle_imu(data):
                print(f"IMU: {data.get('imu')}")
        """
        self._telemetry_callbacks.append(callback)
        return callback

    def on_start(self, callback: LifecycleCallback) -> LifecycleCallback:
        """
        Register a callback to be called when runtime starts.

        Use for setup tasks like arming, calibration, etc.
        Can be used as a decorator.

        Example:
            @runtime.on_start
            async def setup():
                await robot.arm()
        """
        self._start_callbacks.append(callback)
        return callback

    def on_stop(self, callback: LifecycleCallback) -> LifecycleCallback:
        """
        Register a callback to be called when runtime stops.

        Use for cleanup tasks like disarming, stopping motors, etc.
        Can be used as a decorator.

        Example:
            @runtime.on_stop
            async def cleanup():
                await robot.motion.stop()
                await robot.disarm()
        """
        self._stop_callbacks.append(callback)
        return callback

    # --- Lifecycle ---

    async def start(self) -> None:
        """
        Start the runtime loop.

        This sets up telemetry subscriptions and calls on_start callbacks.
        The actual loop runs in run().
        """
        if self._running:
            return

        self._stop_event = asyncio.Event()
        self._tick_count = 0
        self._start_time = time.time()

        # Subscribe to telemetry
        for topic in self._config.telemetry_topics:
            self._robot.on(topic, self._on_telemetry_event)

        # Auto-arm if configured
        if self._config.auto_arm:
            await self._robot.arm()

        # Call start callbacks
        for callback in self._start_callbacks:
            await callback()

        self._running = True

    async def stop(self) -> None:
        """
        Stop the runtime loop.

        This signals the loop to exit and calls on_stop callbacks.
        """
        if not self._running:
            return

        self._running = False
        if self._stop_event:
            self._stop_event.set()

        # Call stop callbacks
        for callback in self._stop_callbacks:
            await callback()

        # Auto-disarm if we auto-armed
        if self._config.auto_arm:
            await self._robot.disarm()

    async def run(self, duration: Optional[float] = None) -> None:
        """
        Run the runtime loop.

        Args:
            duration: Optional duration in seconds. If None, runs until stop() is called.

        Example:
            # Run for 10 seconds
            await runtime.run(duration=10.0)

            # Run indefinitely (until Ctrl+C or stop())
            await runtime.run()
        """
        await self.start()

        try:
            # Use monotonic clock for timing (immune to system clock adjustments)
            monotonic = time.monotonic
            now = monotonic()
            end_time = now + duration if duration else None
            last_tick = now

            # Cache frequently-accessed values for tight loop
            tick_period = self._tick_period
            tick_callbacks = self._tick_callbacks
            stop_on_error = self._config.stop_on_error

            while self._running:
                now = monotonic()

                # Check duration
                if end_time and now >= end_time:
                    break

                # Calculate dt
                dt = now - last_tick
                last_tick = now

                # Call tick callbacks
                for callback in tick_callbacks:
                    try:
                        await callback(dt)
                    except Exception as e:
                        if stop_on_error:
                            raise
                        print(f"[Runtime] Tick callback error: {e}")

                self._tick_count += 1

                # Sleep to maintain tick rate
                elapsed = monotonic() - now
                sleep_time = tick_period - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        finally:
            await self.stop()

    async def run_once(self) -> None:
        """
        Run a single tick of the runtime loop.

        Useful for testing or manual stepping.
        """
        if not self._running:
            await self.start()

        dt = self._tick_period
        for callback in self._tick_callbacks:
            await callback(dt)
        self._tick_count += 1

    # --- Internal ---

    def _on_telemetry_event(self, data: dict) -> None:
        """Internal: dispatch telemetry to registered callbacks."""
        for callback in self._telemetry_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"[Runtime] Telemetry callback error: {e}")

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"Runtime({status}, tick_hz={self._config.tick_hz}, ticks={self._tick_count})"
