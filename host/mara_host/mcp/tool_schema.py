# mara_host/mcp/tool_schema.py
"""
MCP/HTTP Tool Schema - Single source of truth for LLM-accessible tools.

This schema defines all tools exposed via MCP and HTTP servers.
Tools are generated from this schema by `tools/gen_mcp_servers.py`.

Each tool maps to a service method call and specifies:
- name: Tool identifier (becomes mara_<name> for MCP, /<category>/<action> for HTTP)
- description: Human-readable description for LLM
- category: Grouping (connection, state, servo, motor, gpio, stepper, pwm)
- service: Service property on MaraRuntime (or None for special tools)
- method: Method to call on the service
- params: Parameter definitions with JSON Schema types
- requires_arm: Whether to call ensure_armed() before execution
- response: How to format the response
"""

from __future__ import annotations

from typing import Optional, Literal, NamedTuple


class ToolParam(NamedTuple):
    """Parameter definition for a tool."""
    name: str
    type: Literal["integer", "number", "string", "boolean"]
    description: str
    required: bool = True
    default: Optional[any] = None
    # Maps this param to a different name when calling the service method
    service_name: Optional[str] = None


class ToolDef(NamedTuple):
    """Definition of an MCP/HTTP tool."""
    name: str
    description: str
    category: str
    service: Optional[str] = None  # Service property name on runtime
    method: Optional[str] = None   # Method to call on service
    params: tuple[ToolParam, ...] = ()
    requires_arm: bool = True
    # For tools that use client directly instead of service
    client_method: Optional[str] = None
    # Custom response format (None = use default ServiceResult handling)
    response_format: Optional[str] = None
    # For special tools with custom handlers
    custom_handler: bool = False


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS: list[ToolDef] = [
    # ─────────────────────────────────────────────────────────────────────────
    # Connection Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="connect",
        description="Connect to the robot. Auto-connects if needed for other commands.",
        category="connection",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="disconnect",
        description="Disconnect from the robot.",
        category="connection",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="get_state",
        description="Get current robot state including connection, arm status, telemetry, and recent commands.",
        category="state",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="get_freshness",
        description="Get data freshness report - shows which sensor data is fresh, aging, or stale.",
        category="state",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="get_events",
        description="Get recent events (state changes, commands, errors).",
        category="state",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="get_command_stats",
        description="Get command statistics (success rate, latency, pending count).",
        category="state",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="wifi_status",
        description="Get current Wi‑Fi status including STA/AP mode and IPs.",
        category="wifi",
        service="wifi_service",
        method="status",
        requires_arm=False,
    ),
    ToolDef(
        name="wifi_join",
        description="Join a Wi‑Fi network at runtime while keeping AP recovery available.",
        category="wifi",
        service="wifi_service",
        method="join",
        params=(
            ToolParam("ssid", "string", "Wi‑Fi SSID"),
            ToolParam("password", "string", "Wi‑Fi password"),
            ToolParam("wait_for_connect", "boolean", "Wait for connection result before replying", required=False, default=True),
            ToolParam("timeout_ms", "integer", "Join timeout in milliseconds", required=False, default=10000),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="wifi_disconnect",
        description="Disconnect station Wi‑Fi while leaving AP recovery intact.",
        category="wifi",
        service="wifi_service",
        method="disconnect",
        requires_arm=False,
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # State Control Tools (use StateService for convergence with CLI/GUI)
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="arm",
        description="Arm the robot for operation. Required before moving actuators.",
        category="state",
        service="state_service",
        method="arm",
        requires_arm=False,
        response_format="Armed",
    ),
    ToolDef(
        name="disarm",
        description="Disarm the robot. Stops all motion.",
        category="state",
        service="state_service",
        method="disarm",
        requires_arm=False,
        response_format="Disarmed",
    ),
    ToolDef(
        name="stop",
        description="Emergency stop - immediately halt all motion.",
        category="state",
        service="state_service",
        method="stop",
        requires_arm=False,
        response_format="Stopped",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Servo Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="servo_attach",
        description="Attach a servo to a GPIO pin.",
        category="servo",
        service="servo_service",
        method="attach",
        params=(
            ToolParam("servo_id", "integer", "Servo ID (0-7)"),
            ToolParam("pin", "integer", "GPIO pin number", service_name="channel"),
            ToolParam("min_us", "integer", "Min pulse width in microseconds", required=False, default=500),
            ToolParam("max_us", "integer", "Max pulse width in microseconds", required=False, default=2500),
        ),
        response_format="Servo {servo_id} attached to pin {pin}",
    ),
    ToolDef(
        name="servo_set",
        description="Move a servo to the specified angle.",
        category="servo",
        service="servo_service",
        method="set_angle",
        params=(
            ToolParam("servo_id", "integer", "Servo ID (0-7)"),
            ToolParam("angle", "number", "Angle in degrees (0-180)"),
            ToolParam("duration_ms", "integer", "Movement duration in ms (0=instant)", required=False, default=300),
        ),
        response_format="Servo {servo_id} -> {angle}deg",
    ),
    ToolDef(
        name="servo_center",
        description="Move servo to center position (90 degrees).",
        category="servo",
        service="servo_service",
        method="center",
        params=(
            ToolParam("servo_id", "integer", "Servo ID (0-7)"),
        ),
        response_format="Servo {servo_id} centered",
    ),
    ToolDef(
        name="servo_detach",
        description="Detach a servo from its pin.",
        category="servo",
        service="servo_service",
        method="detach",
        params=(
            ToolParam("servo_id", "integer", "Servo ID (0-7)"),
        ),
        response_format="Servo {servo_id} detached",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Motor Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="motor_set",
        description="Set DC motor speed.",
        category="motor",
        service="motor_service",
        method="set_speed",
        params=(
            ToolParam("motor_id", "integer", "Motor ID (0-3)"),
            ToolParam("speed", "number", "Speed (-1.0 to 1.0)"),
        ),
        response_format="Motor {motor_id} -> {speed:.0%}",
    ),
    ToolDef(
        name="motor_stop",
        description="Stop a DC motor.",
        category="motor",
        service="motor_service",
        method="stop",
        params=(
            ToolParam("motor_id", "integer", "Motor ID (0-3)"),
        ),
        response_format="Motor {motor_id} stopped",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # GPIO Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="gpio_write",
        description="Set GPIO pin high or low.",
        category="gpio",
        service="gpio_service",
        method="write",
        params=(
            ToolParam("channel", "integer", "GPIO channel ID"),
            ToolParam("value", "integer", "0=low, 1=high"),
        ),
        response_format="GPIO {channel} set to {value}",
    ),
    ToolDef(
        name="gpio_toggle",
        description="Toggle GPIO pin state.",
        category="gpio",
        service="gpio_service",
        method="toggle",
        params=(
            ToolParam("channel", "integer", "GPIO channel ID"),
        ),
        response_format="GPIO {channel} toggled",
    ),
    ToolDef(
        name="gpio_read",
        description="Read GPIO pin state.",
        category="gpio",
        service="gpio_service",
        method="read",
        params=(
            ToolParam("channel", "integer", "GPIO channel ID"),
        ),
        requires_arm=False,
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Stepper Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="stepper_move",
        description="Move stepper motor by relative steps.",
        category="stepper",
        service="stepper_service",
        method="move_relative",
        params=(
            ToolParam("stepper_id", "integer", "Stepper ID"),
            ToolParam("steps", "integer", "Steps to move (negative=reverse)"),
            ToolParam("speed", "number", "Speed in steps/second", required=False, default=None),
        ),
        response_format="Stepper {stepper_id} moved {steps} steps",
    ),
    ToolDef(
        name="stepper_stop",
        description="Stop a stepper motor.",
        category="stepper",
        service="stepper_service",
        method="stop",
        params=(
            ToolParam("stepper_id", "integer", "Stepper ID"),
        ),
        response_format="Stepper {stepper_id} stopped",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # PWM Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="pwm_set",
        description="Set PWM duty cycle on a channel.",
        category="pwm",
        service="pwm_service",
        method="set_duty",
        params=(
            ToolParam("channel", "integer", "PWM channel"),
            ToolParam("duty", "number", "Duty cycle (0.0-1.0)"),
        ),
        response_format="PWM {channel} -> {duty:.0%}",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Encoder Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="encoder_read",
        description="Read encoder value.",
        category="encoder",
        service="encoder_service",
        method="read",
        params=(
            ToolParam("encoder_id", "integer", "Encoder ID"),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="encoder_reset",
        description="Reset encoder count to zero.",
        category="encoder",
        service="encoder_service",
        method="reset",
        params=(
            ToolParam("encoder_id", "integer", "Encoder ID"),
        ),
        response_format="Encoder {encoder_id} reset",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # IMU Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="imu_read",
        description="Read IMU sensor data (accelerometer and gyroscope).",
        category="imu",
        service="imu_service",
        method="read",
        params=(),
        requires_arm=False,
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Ultrasonic Tools
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="ultrasonic_attach",
        description="Attach an ultrasonic distance sensor to GPIO pins.",
        category="ultrasonic",
        service="ultrasonic_service",
        method="attach",
        params=(
            ToolParam("sensor_id", "integer", "Sensor ID (0-3)"),
            ToolParam("trig_pin", "integer", "Trigger GPIO pin"),
            ToolParam("echo_pin", "integer", "Echo GPIO pin"),
            ToolParam("max_distance_cm", "number", "Maximum measurable distance in cm", required=False, default=400.0),
        ),
        requires_arm=False,
        response_format="Ultrasonic {sensor_id} attached (trig={trig_pin}, echo={echo_pin})",
    ),
    ToolDef(
        name="ultrasonic_read",
        description="Read distance from ultrasonic sensor in centimeters.",
        category="ultrasonic",
        service="ultrasonic_service",
        method="read",
        params=(
            ToolParam("sensor_id", "integer", "Sensor ID (0-3)"),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="ultrasonic_detach",
        description="Detach an ultrasonic sensor.",
        category="ultrasonic",
        service="ultrasonic_service",
        method="detach",
        params=(
            ToolParam("sensor_id", "integer", "Sensor ID (0-3)"),
        ),
        requires_arm=False,
        response_format="Ultrasonic {sensor_id} detached",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Robot Tools (semantic abstraction layer)
    # ─────────────────────────────────────────────────────────────────────────
    ToolDef(
        name="robot_describe",
        description="Get robot structure: joints, their limits, relationships, and what each controls. Call this first to understand what you're controlling.",
        category="robot",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="robot_state",
        description="Get complete robot status: safety state (IDLE/ARMED/ESTOP), current joint positions with freshness indicators, and sensor readings.",
        category="robot",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="robot_pose",
        description="Get current position of all joints by name, with percentage of range and freshness indicators.",
        category="robot",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="robot_move",
        description="Move one or more joints by name. Joints move simultaneously. Provide moves as JSON array.",
        category="robot",
        service="robot_service",
        method="move_joints",
        params=(
            ToolParam("moves", "string", "JSON array of moves, e.g. [{joint: shoulder, angle: 45}]"),
            ToolParam("duration_ms", "integer", "Movement duration in milliseconds", required=False, default=300),
        ),
        response_format="Moved: {moved}",
    ),
    ToolDef(
        name="robot_home",
        description="Move all joints (or specified joints) to their home positions.",
        category="robot",
        service="robot_service",
        method="home",
        params=(
            ToolParam("joints", "string", "JSON array of joint names to home, or omit for all joints", required=False, default=None),
            ToolParam("duration_ms", "integer", "Movement duration in milliseconds", required=False, default=500),
        ),
        response_format="Homed",
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_tools_by_category(category: str) -> list[ToolDef]:
    """Get all tools in a category."""
    return [t for t in TOOLS if t.category == category]


def get_tool_by_name(name: str) -> Optional[ToolDef]:
    """Get a tool by name."""
    for t in TOOLS:
        if t.name == name:
            return t
    return None


def get_all_categories() -> list[str]:
    """Get list of all tool categories."""
    return sorted(set(t.category for t in TOOLS))
