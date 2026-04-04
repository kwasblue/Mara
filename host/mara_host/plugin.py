# mara_host/plugin.py
"""
MARA Plugin API.

This module provides the public API for writing MARA plugins.
Plugins are single Python files placed in ~/.mara/plugins/.

Example plugin (~/.mara/plugins/my_plugin.py):

    # Dict style - simple and familiar
    TOOLS = [
        {
            "name": "my_wiggle",
            "description": "Wiggle a servo back and forth",
            "params": [
                {"name": "servo_id", "type": "integer", "description": "Servo to wiggle"},
                {"name": "count", "type": "integer", "description": "Number of wiggles", "default": 3},
            ],
        }
    ]

    async def my_wiggle(api, servo_id: int, count: int = 3) -> dict:
        import asyncio

        await api.ensure_connected()
        for i in range(count):
            await api.servo.set_angle(servo_id, 45)
            await asyncio.sleep(0.3)
            await api.servo.set_angle(servo_id, 135)
            await asyncio.sleep(0.3)
        await api.servo.set_angle(servo_id, 90)
        return {"wiggles": count, "servo_id": servo_id}


    # OR Dataclass style - more structured
    class WiggleServo(ToolDef):
        name = "wiggle_servo"
        description = "Wiggle a servo back and forth"
        params = [
            ToolParam("servo_id", "integer", "Servo to wiggle"),
            ToolParam("count", "integer", "Number of wiggles", required=False, default=3),
        ]

        async def run(self, api, servo_id: int, count: int = 3) -> dict:
            import asyncio

            await api.ensure_connected()
            for i in range(count):
                await api.servo.set_angle(servo_id, 45)
                await asyncio.sleep(0.3)
                await api.servo.set_angle(servo_id, 135)
                await asyncio.sleep(0.3)
            await api.servo.set_angle(servo_id, 90)
            return {"wiggles": count, "servo_id": servo_id}


The MaraPluginAPI provides access to:
    - api.connected (bool) - Connection status
    - api.connect() / api.disconnect() - Connection management
    - api.ensure_connected() - Connect if not connected
    - api.get_state() - Current state snapshot
    - api.robot_state - Current mode (IDLE/ARMED/ACTIVE)
    - api.servo - ServoService
    - api.motor - MotorService
    - api.gpio - GPIOService
    - api.imu - IMUService
    - api.encoder - EncoderService
    - api.stepper - StepperService
    - api.signals - SignalService
    - api.control_graph - ControlGraphService
    - api.motion - MotionService
    - api.state_service - StateService (arm/disarm/stop)
    - api.client - Low-level client (advanced)
"""

from mara_host.mcp.plugin_loader import (
    ToolDef,
    ToolParam,
    MaraPluginAPI,
)

__all__ = [
    "ToolDef",
    "ToolParam",
    "MaraPluginAPI",
]
