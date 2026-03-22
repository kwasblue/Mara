#!/usr/bin/env python3
# mara_host/mcp/server.py
"""
MCP server for MARA robot control.

Exposes robot control and telemetry as MCP tools.

Usage:
    python -m mara_host.mcp.server

    # Or with options:
    python -m mara_host.mcp.server --port /dev/cu.usbserial-0001
    python -m mara_host.mcp.server --tcp 192.168.4.1
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mara_host.mcp.runtime import MaraRuntime


def create_server(
    port: str | None = None,
    host: str | None = None,
    tcp_port: int = 3333,
) -> Server:
    """Create and configure the MCP server."""

    server = Server("mara")
    runtime = MaraRuntime(port=port, host=host, tcp_port=tcp_port)

    # ═══════════════════════════════════════════════════════════
    # Tool Definitions
    # ═══════════════════════════════════════════════════════════

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # Connection
            Tool(
                name="mara_connect",
                description="Connect to the robot. Auto-connects if needed for other commands.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mara_disconnect",
                description="Disconnect from the robot.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mara_get_state",
                description="Get current robot state including connection, arm status, telemetry, and recent commands.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),

            # State control
            Tool(
                name="mara_arm",
                description="Arm the robot for operation. Required before moving actuators.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mara_disarm",
                description="Disarm the robot. Stops all motion.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="mara_stop",
                description="Emergency stop - immediately halt all motion.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),

            # Servo control
            Tool(
                name="mara_servo_attach",
                description="Attach a servo to a GPIO pin.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "servo_id": {"type": "integer", "description": "Servo ID (0-7)"},
                        "pin": {"type": "integer", "description": "GPIO pin number"},
                        "min_us": {"type": "integer", "description": "Min pulse width in microseconds (default: 500)", "default": 500},
                        "max_us": {"type": "integer", "description": "Max pulse width in microseconds (default: 2500)", "default": 2500},
                    },
                    "required": ["servo_id", "pin"],
                },
            ),
            Tool(
                name="mara_servo_set",
                description="Move a servo to the specified angle.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "servo_id": {"type": "integer", "description": "Servo ID (0-7)"},
                        "angle": {"type": "number", "description": "Angle in degrees (0-180)"},
                        "duration_ms": {"type": "integer", "description": "Movement duration in ms (0=instant)", "default": 0},
                    },
                    "required": ["servo_id", "angle"],
                },
            ),
            Tool(
                name="mara_servo_center",
                description="Move servo to center position (90 degrees).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "servo_id": {"type": "integer", "description": "Servo ID (0-7)"},
                    },
                    "required": ["servo_id"],
                },
            ),

            # Motor control
            Tool(
                name="mara_motor_set",
                description="Set DC motor speed.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "motor_id": {"type": "integer", "description": "Motor ID"},
                        "speed": {"type": "number", "description": "Speed (-1.0 to 1.0)"},
                    },
                    "required": ["motor_id", "speed"],
                },
            ),
            Tool(
                name="mara_motor_stop",
                description="Stop a DC motor.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "motor_id": {"type": "integer", "description": "Motor ID"},
                    },
                    "required": ["motor_id"],
                },
            ),

            # GPIO control
            Tool(
                name="mara_gpio_write",
                description="Set GPIO pin high or low.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "integer", "description": "GPIO channel ID"},
                        "value": {"type": "integer", "description": "0=low, 1=high"},
                    },
                    "required": ["channel", "value"],
                },
            ),
            Tool(
                name="mara_gpio_toggle",
                description="Toggle GPIO pin state.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "integer", "description": "GPIO channel ID"},
                    },
                    "required": ["channel"],
                },
            ),

            # Stepper control
            Tool(
                name="mara_stepper_move",
                description="Move stepper motor by relative steps.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stepper_id": {"type": "integer", "description": "Stepper ID"},
                        "steps": {"type": "integer", "description": "Steps to move (negative=reverse)"},
                        "speed": {"type": "number", "description": "Speed in steps/second"},
                    },
                    "required": ["stepper_id", "steps"],
                },
            ),

            # PWM control
            Tool(
                name="mara_pwm_set",
                description="Set PWM duty cycle on a channel.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "integer", "description": "PWM channel"},
                        "duty": {"type": "number", "description": "Duty cycle (0.0-1.0)"},
                    },
                    "required": ["channel", "duty"],
                },
            ),
        ]

    # ═══════════════════════════════════════════════════════════
    # Tool Implementations
    # ═══════════════════════════════════════════════════════════

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool and return result."""

        try:
            result = await _execute_tool(runtime, name, arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def _execute_tool(runtime: MaraRuntime, name: str, args: dict) -> str:
    """Execute a tool by name."""

    # Auto-connect and arm for actuator tools
    if name not in ("mara_connect", "mara_disconnect", "mara_get_state"):
        await runtime.ensure_armed()

    # ─────────────────────────────────────────────────────────
    # Connection tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_connect":
        result = await runtime.connect()
        return f"Connected: {result}"

    if name == "mara_disconnect":
        result = await runtime.disconnect()
        return f"Disconnected: {result}"

    if name == "mara_get_state":
        if not runtime.is_connected:
            return "Not connected. Use mara_connect first."
        return str(runtime.get_snapshot())

    # ─────────────────────────────────────────────────────────
    # State control
    # ─────────────────────────────────────────────────────────

    if name == "mara_arm":
        ok, err = await runtime.client.arm()
        runtime.record_command("arm", {}, ok, err)
        return "✓ Armed" if ok else f"✗ Arm failed: {err}"

    if name == "mara_disarm":
        ok, err = await runtime.client.disarm()
        runtime.record_command("disarm", {}, ok, err)
        return "✓ Disarmed" if ok else f"✗ Disarm failed: {err}"

    if name == "mara_stop":
        ok, err = await runtime.client.cmd_stop()
        runtime.record_command("stop", {}, ok, err)
        return "✓ Stopped" if ok else f"✗ Stop failed: {err}"

    # ─────────────────────────────────────────────────────────
    # Servo tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_servo_attach":
        servo_id = args["servo_id"]
        pin = args["pin"]
        min_us = args.get("min_us", 500)
        max_us = args.get("max_us", 2500)
        result = await runtime.servo_service.attach(servo_id, channel=pin, min_us=min_us, max_us=max_us)
        runtime.record_command("servo_attach", args, result.ok, result.error)
        if result.ok:
            return f"✓ Servo {servo_id} attached to pin {pin} (pulse: {min_us}-{max_us}µs)"
        return f"✗ Attach failed: {result.error}"

    if name == "mara_servo_set":
        servo_id = args["servo_id"]
        angle = args["angle"]
        duration_ms = args.get("duration_ms", 300)  # Default to 300ms for smooth movement
        result = await runtime.servo_service.set_angle(servo_id, angle, duration_ms=duration_ms)
        runtime.record_command("servo_set", args, result.ok, result.error)
        if result.ok:
            return f"✓ Servo {servo_id} → {angle}°"
        return f"✗ Set failed: {result.error}"

    if name == "mara_servo_center":
        servo_id = args["servo_id"]
        result = await runtime.servo_service.center(servo_id)
        runtime.record_command("servo_center", args, result.ok, result.error)
        if result.ok:
            return f"✓ Servo {servo_id} → 90° (centered)"
        return f"✗ Center failed: {result.error}"

    # ─────────────────────────────────────────────────────────
    # Motor tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_motor_set":
        motor_id = args["motor_id"]
        speed = args["speed"]
        result = await runtime.motor_service.set_speed(motor_id, speed)
        runtime.record_command("motor_set", args, result.ok, result.error)
        if result.ok:
            return f"✓ Motor {motor_id} → {speed:.0%}"
        return f"✗ Set failed: {result.error}"

    if name == "mara_motor_stop":
        motor_id = args["motor_id"]
        result = await runtime.motor_service.stop(motor_id)
        runtime.record_command("motor_stop", args, result.ok, result.error)
        if result.ok:
            return f"✓ Motor {motor_id} stopped"
        return f"✗ Stop failed: {result.error}"

    # ─────────────────────────────────────────────────────────
    # GPIO tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_gpio_write":
        channel = args["channel"]
        value = args["value"]
        result = await runtime.gpio_service.write(channel, value)
        runtime.record_command("gpio_write", args, result.ok, result.error)
        if result.ok:
            return f"✓ GPIO {channel} → {'HIGH' if value else 'LOW'}"
        return f"✗ Write failed: {result.error}"

    if name == "mara_gpio_toggle":
        channel = args["channel"]
        result = await runtime.gpio_service.toggle(channel)
        runtime.record_command("gpio_toggle", args, result.ok, result.error)
        if result.ok:
            return f"✓ GPIO {channel} toggled"
        return f"✗ Toggle failed: {result.error}"

    # ─────────────────────────────────────────────────────────
    # Stepper tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_stepper_move":
        stepper_id = args["stepper_id"]
        steps = args["steps"]
        speed = args.get("speed")
        result = await runtime.stepper_service.move_relative(stepper_id, steps, speed=speed)
        runtime.record_command("stepper_move", args, result.ok, result.error)
        if result.ok:
            return f"✓ Stepper {stepper_id} moved {steps} steps"
        return f"✗ Move failed: {result.error}"

    # ─────────────────────────────────────────────────────────
    # PWM tools
    # ─────────────────────────────────────────────────────────

    if name == "mara_pwm_set":
        channel = args["channel"]
        duty = args["duty"]
        result = await runtime.pwm_service.set_duty(channel, duty)
        runtime.record_command("pwm_set", args, result.ok, result.error)
        if result.ok:
            return f"✓ PWM {channel} → {duty:.0%}"
        return f"✗ Set failed: {result.error}"

    return f"Unknown tool: {name}"


async def main():
    """Run the MCP or HTTP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MARA Server - MCP or HTTP mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # MCP mode (for Claude Code)
  python -m mara_host.mcp

  # HTTP mode (for any LLM)
  python -m mara_host.mcp --http
  python -m mara_host.mcp --http --http-port 8080

  # With specific serial port
  python -m mara_host.mcp -p /dev/ttyUSB0

  # With TCP connection
  python -m mara_host.mcp --tcp 192.168.4.1
"""
    )
    parser.add_argument("-p", "--port", help="Serial port (default: from config)")
    parser.add_argument("--tcp", metavar="HOST", help="TCP host (instead of serial)")
    parser.add_argument("--tcp-port", type=int, default=3333, help="TCP port (default: 3333)")
    parser.add_argument("--http", action="store_true", help="Run HTTP server instead of MCP")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()

    # Get port from args or environment or config
    port = args.port or os.environ.get("MARA_PORT")
    host = args.tcp or os.environ.get("MARA_HOST")
    tcp_port = args.tcp_port or int(os.environ.get("MARA_TCP_PORT", "3333"))

    # Default to config if nothing specified
    if not port and not host:
        from mara_host.cli.cli_config import get_serial_port
        port = get_serial_port()

    if args.http:
        # HTTP mode
        from mara_host.mcp.http_server import run_http_server
        await run_http_server(
            port=port,
            host=host,
            tcp_port=tcp_port,
            http_port=args.http_port,
        )
    else:
        # MCP mode
        server = create_server(port=port, host=host, tcp_port=tcp_port)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
