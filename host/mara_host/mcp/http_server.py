# mara_host/mcp/http_server.py
"""
HTTP API server for MARA robot control.

Provides REST endpoints for any LLM with function calling.

Usage:
    python -m mara_host.mcp --http
    python -m mara_host.mcp --http --http-port 8080
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mara_host.mcp.runtime import MaraRuntime


def create_http_app(runtime: MaraRuntime) -> Starlette:
    """Create HTTP API application."""

    @asynccontextmanager
    async def lifespan(app):
        # Connect on startup
        try:
            await runtime.connect()
            print(f"[MARA HTTP] Connected to robot")
        except Exception as e:
            print(f"[MARA HTTP] Connection failed: {e}")
        yield
        # Disconnect on shutdown
        await runtime.disconnect()
        print("[MARA HTTP] Disconnected")

    # ═══════════════════════════════════════════════════════════
    # Endpoints
    # ═══════════════════════════════════════════════════════════

    async def get_state(request: Request) -> JSONResponse:
        """GET /state - Get full robot state."""
        if not runtime.is_connected:
            return JSONResponse({"error": "not_connected"}, status_code=503)
        return JSONResponse(runtime.get_snapshot())

    async def post_connect(request: Request) -> JSONResponse:
        """POST /connect - Connect to robot."""
        result = await runtime.connect()
        return JSONResponse(result)

    async def post_disconnect(request: Request) -> JSONResponse:
        """POST /disconnect - Disconnect from robot."""
        result = await runtime.disconnect()
        return JSONResponse(result)

    async def post_arm(request: Request) -> JSONResponse:
        """POST /arm - Arm the robot."""
        await runtime.ensure_connected()
        ok, err = await runtime.client.arm()
        runtime.record_command("arm", {}, ok, err)
        return JSONResponse({"ok": ok, "error": err})

    async def post_disarm(request: Request) -> JSONResponse:
        """POST /disarm - Disarm the robot."""
        await runtime.ensure_connected()
        ok, err = await runtime.client.disarm()
        runtime.record_command("disarm", {}, ok, err)
        return JSONResponse({"ok": ok, "error": err})

    async def post_stop(request: Request) -> JSONResponse:
        """POST /stop - Emergency stop."""
        await runtime.ensure_connected()
        ok, err = await runtime.client.cmd_stop()
        runtime.record_command("stop", {}, ok, err)
        return JSONResponse({"ok": ok, "error": err})

    # ─────────────────────────────────────────────────────────
    # Servo endpoints
    # ─────────────────────────────────────────────────────────

    async def post_servo_attach(request: Request) -> JSONResponse:
        """POST /servo/attach - Attach servo to pin."""
        await runtime.ensure_armed()
        body = await request.json()
        servo_id = body.get("servo_id", 0)
        pin = body.get("pin")
        min_us = body.get("min_us", 500)
        max_us = body.get("max_us", 2500)
        if pin is None:
            return JSONResponse({"ok": False, "error": "pin required"}, status_code=400)
        result = await runtime.servo_service.attach(servo_id, channel=pin, min_us=min_us, max_us=max_us)
        runtime.record_command("servo_attach", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    async def post_servo_set(request: Request) -> JSONResponse:
        """POST /servo/set - Set servo angle."""
        await runtime.ensure_armed()
        body = await request.json()
        servo_id = body.get("servo_id", 0)
        angle = body.get("angle")
        duration_ms = body.get("duration_ms", 300)  # Default to 300ms for smooth movement
        if angle is None:
            return JSONResponse({"ok": False, "error": "angle required"}, status_code=400)
        result = await runtime.servo_service.set_angle(servo_id, angle, duration_ms=duration_ms)
        runtime.record_command("servo_set", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error, "angle": angle})

    async def post_servo_center(request: Request) -> JSONResponse:
        """POST /servo/center - Center servo."""
        await runtime.ensure_armed()
        body = await request.json()
        servo_id = body.get("servo_id", 0)
        result = await runtime.servo_service.center(servo_id)
        runtime.record_command("servo_center", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    # ─────────────────────────────────────────────────────────
    # Motor endpoints
    # ─────────────────────────────────────────────────────────

    async def post_motor_set(request: Request) -> JSONResponse:
        """POST /motor/set - Set motor speed."""
        await runtime.ensure_armed()
        body = await request.json()
        motor_id = body.get("motor_id", 0)
        speed = body.get("speed")
        if speed is None:
            return JSONResponse({"ok": False, "error": "speed required"}, status_code=400)
        result = await runtime.motor_service.set_speed(motor_id, speed)
        runtime.record_command("motor_set", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    async def post_motor_stop(request: Request) -> JSONResponse:
        """POST /motor/stop - Stop motor."""
        await runtime.ensure_armed()
        body = await request.json()
        motor_id = body.get("motor_id", 0)
        result = await runtime.motor_service.stop(motor_id)
        runtime.record_command("motor_stop", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    # ─────────────────────────────────────────────────────────
    # GPIO endpoints
    # ─────────────────────────────────────────────────────────

    async def post_gpio_write(request: Request) -> JSONResponse:
        """POST /gpio/write - Write GPIO value."""
        await runtime.ensure_armed()
        body = await request.json()
        channel = body.get("channel", 0)
        value = body.get("value")
        if value is None:
            return JSONResponse({"ok": False, "error": "value required"}, status_code=400)
        result = await runtime.gpio_service.write(channel, value)
        runtime.record_command("gpio_write", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    async def post_gpio_toggle(request: Request) -> JSONResponse:
        """POST /gpio/toggle - Toggle GPIO."""
        await runtime.ensure_armed()
        body = await request.json()
        channel = body.get("channel", 0)
        result = await runtime.gpio_service.toggle(channel)
        runtime.record_command("gpio_toggle", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    # ─────────────────────────────────────────────────────────
    # Stepper endpoints
    # ─────────────────────────────────────────────────────────

    async def post_stepper_move(request: Request) -> JSONResponse:
        """POST /stepper/move - Move stepper."""
        await runtime.ensure_armed()
        body = await request.json()
        stepper_id = body.get("stepper_id", 0)
        steps = body.get("steps")
        speed = body.get("speed")
        if steps is None:
            return JSONResponse({"ok": False, "error": "steps required"}, status_code=400)
        result = await runtime.stepper_service.move_relative(stepper_id, steps, speed=speed)
        runtime.record_command("stepper_move", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    # ─────────────────────────────────────────────────────────
    # PWM endpoints
    # ─────────────────────────────────────────────────────────

    async def post_pwm_set(request: Request) -> JSONResponse:
        """POST /pwm/set - Set PWM duty."""
        await runtime.ensure_armed()
        body = await request.json()
        channel = body.get("channel", 0)
        duty = body.get("duty")
        if duty is None:
            return JSONResponse({"ok": False, "error": "duty required"}, status_code=400)
        result = await runtime.pwm_service.set_duty(channel, duty)
        runtime.record_command("pwm_set", body, result.ok, result.error)
        return JSONResponse({"ok": result.ok, "error": result.error})

    # ─────────────────────────────────────────────────────────
    # Debug endpoint
    # ─────────────────────────────────────────────────────────

    async def post_servo_test(request: Request) -> JSONResponse:
        """POST /servo/test - Debug: test servo with full logging."""
        import sys
        await runtime.ensure_connected()
        body = await request.json()
        servo_id = body.get("servo_id", 0)
        pin = body.get("pin", 13)
        angle = body.get("angle", 90)

        logs = []
        set_result = None

        # Check client state
        logs.append(f"Client connected: {runtime.client._running}")
        logs.append(f"Robot state: {runtime.state.robot_state}")

        # Ensure armed
        arm_ok, arm_err = await runtime.client.arm()
        logs.append(f"Arm: ok={arm_ok}, error={arm_err}")

        # Attach with explicit parameters (no detach needed - attach handles it)
        logs.append(f"Attaching servo {servo_id} to pin {pin} (500-2500µs)")
        attach_result = await runtime.servo_service.attach(servo_id, channel=pin, min_us=500, max_us=2500)
        logs.append(f"Attach result: ok={attach_result.ok}, error={attach_result.error}")

        if attach_result.ok:
            # Set angle
            logs.append(f"Setting angle to {angle}°")
            set_result = await runtime.servo_service.set_angle(servo_id, angle, duration_ms=500)
            logs.append(f"Set result: ok={set_result.ok}, error={set_result.error}")

        # Print to server console too
        for log in logs:
            print(f"[SERVO TEST] {log}", file=sys.stderr)

        return JSONResponse({
            "logs": logs,
            "ok": attach_result.ok and (set_result.ok if set_result else False)
        })

    # ─────────────────────────────────────────────────────────
    # Schema endpoint (for LLM function definitions)
    # ─────────────────────────────────────────────────────────

    async def get_schema(request: Request) -> JSONResponse:
        """GET /schema - Get OpenAI-compatible function definitions."""
        return JSONResponse({
            "functions": [
                {
                    "name": "mara_get_state",
                    "description": "Get current robot state including connection, arm status, and telemetry",
                    "parameters": {"type": "object", "properties": {}}
                },
                {
                    "name": "mara_servo_set",
                    "description": "Move a servo to the specified angle (0-180 degrees)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "servo_id": {"type": "integer", "description": "Servo ID (0-7)"},
                            "angle": {"type": "number", "description": "Angle in degrees (0-180)"},
                            "duration_ms": {"type": "integer", "description": "Movement duration in ms"}
                        },
                        "required": ["servo_id", "angle"]
                    }
                },
                {
                    "name": "mara_motor_set",
                    "description": "Set DC motor speed (-1.0 to 1.0)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "motor_id": {"type": "integer", "description": "Motor ID"},
                            "speed": {"type": "number", "description": "Speed (-1.0 to 1.0)"}
                        },
                        "required": ["motor_id", "speed"]
                    }
                },
                {
                    "name": "mara_gpio_write",
                    "description": "Set GPIO pin high (1) or low (0)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "channel": {"type": "integer", "description": "GPIO channel"},
                            "value": {"type": "integer", "description": "0=low, 1=high"}
                        },
                        "required": ["channel", "value"]
                    }
                },
                {
                    "name": "mara_stop",
                    "description": "Emergency stop - halt all motion",
                    "parameters": {"type": "object", "properties": {}}
                },
            ]
        })

    # ═══════════════════════════════════════════════════════════
    # Routes
    # ═══════════════════════════════════════════════════════════

    routes = [
        # State
        Route("/state", get_state, methods=["GET"]),
        Route("/schema", get_schema, methods=["GET"]),
        Route("/connect", post_connect, methods=["POST"]),
        Route("/disconnect", post_disconnect, methods=["POST"]),

        # Control
        Route("/arm", post_arm, methods=["POST"]),
        Route("/disarm", post_disarm, methods=["POST"]),
        Route("/stop", post_stop, methods=["POST"]),

        # Servo
        Route("/servo/attach", post_servo_attach, methods=["POST"]),
        Route("/servo/set", post_servo_set, methods=["POST"]),
        Route("/servo/center", post_servo_center, methods=["POST"]),
        Route("/servo/test", post_servo_test, methods=["POST"]),

        # Motor
        Route("/motor/set", post_motor_set, methods=["POST"]),
        Route("/motor/stop", post_motor_stop, methods=["POST"]),

        # GPIO
        Route("/gpio/write", post_gpio_write, methods=["POST"]),
        Route("/gpio/toggle", post_gpio_toggle, methods=["POST"]),

        # Stepper
        Route("/stepper/move", post_stepper_move, methods=["POST"]),

        # PWM
        Route("/pwm/set", post_pwm_set, methods=["POST"]),
    ]

    return Starlette(routes=routes, lifespan=lifespan)


async def run_http_server(
    port: Optional[str] = None,
    host: Optional[str] = None,
    tcp_port: int = 3333,
    http_port: int = 8000,
) -> None:
    """Run the HTTP server."""
    import uvicorn

    runtime = MaraRuntime(port=port, host=host, tcp_port=tcp_port)
    app = create_http_app(runtime)

    print(f"[MARA HTTP] Starting server on http://localhost:{http_port}")
    print(f"[MARA HTTP] Endpoints:")
    print(f"  GET  /state     - Get robot state")
    print(f"  GET  /schema    - Get function definitions for LLMs")
    print(f"  POST /servo/set - Move servo")
    print(f"  POST /motor/set - Set motor speed")
    print(f"  POST /gpio/write - Set GPIO")
    print(f"  POST /stop      - Emergency stop")
    print()

    config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
