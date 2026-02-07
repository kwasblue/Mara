# robot_host/runtime/__init__.py
"""
Runtime package - Canonical entrypoint for robot applications.

This package provides the "blessed" way to build robot applications:
- Structured control loop with configurable tick rate
- Module lifecycle management
- Telemetry integration
- Graceful start/stop

Example:
    from robot_host import Robot
    from robot_host.runtime import Runtime

    async def main():
        async with Robot("/dev/ttyUSB0") as robot:
            runtime = Runtime(robot, tick_hz=50.0)

            @runtime.on_tick
            async def control(dt: float):
                await robot.motion.set_velocity(0.1, 0.0)

            @runtime.on_telemetry
            def log_imu(data):
                if "imu" in data:
                    print(f"IMU: {data['imu']}")

            @runtime.on_start
            async def setup():
                await robot.arm()

            @runtime.on_stop
            async def cleanup():
                await robot.disarm()

            # Run for 10 seconds
            await runtime.run(duration=10.0)

    asyncio.run(main())
"""

from .runtime import Runtime, RuntimeConfig

__all__ = [
    "Runtime",
    "RuntimeConfig",
]
