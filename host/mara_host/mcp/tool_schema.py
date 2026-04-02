# mara_host/mcp/tool_schema.py
"""
MCP Tool Schema - Host-only tools that don't map to firmware commands.

This module defines tools for host-side functionality:
- Connection management (connect, disconnect)
- State queries (get_state, get_freshness, get_events, etc.)
- Robot abstraction layer (robot_describe, robot_state, robot_pose)
- Testing (firmware_test, host_test, robot_test_*)
- Recording (record_start, record_stop, record_list, record_status)

Firmware command tools are auto-generated from the command schema.
See `tools/gen_mcp_servers.py` for the generation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal, Any, Mapping


JsonType = Literal["integer", "number", "string", "boolean", "array", "object"]
JsonSchemaDict = dict[str, Any]


@dataclass(frozen=True)
class ToolParam:
    """Typed parameter definition for a tool."""

    name: str
    type: JsonType
    description: str
    required: bool = True
    default: Any = None
    # Maps this param to a different name when calling the service method
    service_name: Optional[str] = None
    # Optional richer JSON Schema override for object/array params.
    json_schema: Optional[Mapping[str, Any]] = None

    def to_json_schema(self) -> JsonSchemaDict:
        """Convert this typed parameter to a JSON Schema property."""
        if self.json_schema is not None:
            schema = dict(self.json_schema)
            schema.setdefault("description", self.description)
            return schema

        schema: JsonSchemaDict = {
            "type": self.type,
            "description": self.description,
        }
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass(frozen=True)
class ToolDef:
    """Typed definition of an MCP/HTTP tool."""

    name: str
    description: str
    category: str
    service: Optional[str] = None  # Service property name on runtime
    method: Optional[str] = None   # Method to call on service
    params: tuple[ToolParam, ...] = field(default_factory=tuple)
    requires_arm: bool = True
    # For tools that use client directly instead of service
    client_method: Optional[str] = None
    # Custom response format (None = use default ServiceResult handling)
    response_format: Optional[str] = None
    # For special tools with custom handlers
    custom_handler: bool = False

    def input_schema(self) -> JsonSchemaDict:
        """Return the canonical MCP/OpenAI input schema for this tool."""
        properties: JsonSchemaDict = {}
        required: list[str] = []

        for param in self.params:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        schema: JsonSchemaDict = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema


# =============================================================================
# Host-Only Tools (custom handlers, not auto-generated from commands)
# =============================================================================

HOST_TOOLS: list[ToolDef] = [
    # -------------------------------------------------------------------------
    # Connection Tools
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # State Query Tools
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Robot Abstraction Tools
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Recording Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="record_start",
        description="Start recording robot telemetry to a session file.",
        category="recording",
        requires_arm=False,
        custom_handler=True,
        params=(
            ToolParam("session_name", "string", "Name for the recording session", required=False, default=None),
        ),
    ),
    ToolDef(
        name="record_stop",
        description="Stop the current recording session and save to disk.",
        category="recording",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="record_list",
        description="List available recording sessions.",
        category="recording",
        requires_arm=False,
        custom_handler=True,
    ),
    ToolDef(
        name="record_status",
        description="Get current recording status.",
        category="recording",
        requires_arm=False,
        custom_handler=True,
    ),

    # -------------------------------------------------------------------------
    # Testing Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="firmware_test",
        description="Run firmware unit tests locally using PlatformIO. Does not require robot connection.",
        category="testing",
        custom_handler=True,
        requires_arm=False,
        params=(
            ToolParam("environments", "string", "Comma-separated environments: native,device", required=False, default="native"),
            ToolParam("filter", "string", "Glob pattern to filter tests", required=False, default=None),
            ToolParam("verbose", "boolean", "Enable verbose output", required=False, default=False),
        ),
    ),
    ToolDef(
        name="robot_test_connection",
        description="Test robot connection with a ping/pong round-trip.",
        category="testing",
        custom_handler=True,
        requires_arm=False,
    ),
    ToolDef(
        name="robot_test_latency",
        description="Measure command round-trip latency over multiple samples.",
        category="testing",
        custom_handler=True,
        requires_arm=False,
        params=(
            ToolParam("samples", "integer", "Number of samples to take", required=False, default=10),
        ),
    ),
    ToolDef(
        name="robot_test_all",
        description="Run all robot hardware self-tests (connection, motors, servos, GPIO).",
        category="testing",
        custom_handler=True,
        requires_arm=False,
    ),
    ToolDef(
        name="host_test",
        description="Run Python host tests via pytest. Does not require robot connection.",
        category="testing",
        custom_handler=True,
        requires_arm=False,
        params=(
            ToolParam("filter", "string", "Pytest filter expression (e.g., 'test_client' or 'tests/test_protocol.py')", required=False, default=None),
            ToolParam("markers", "string", "Pytest markers filter (e.g., 'not slow')", required=False, default=None),
            ToolParam("verbose", "boolean", "Enable verbose pytest output", required=False, default=False),
            ToolParam("timeout", "integer", "Test timeout in seconds (default 300)", required=False, default=300),
        ),
    ),
]

# =============================================================================
# Service-Level Tools (convenience wrappers that don't have direct firmware commands)
# =============================================================================

SERVICE_TOOLS: list[ToolDef] = [
    # -------------------------------------------------------------------------
    # State Control Tools (use StateService for proper state tracking)
    # -------------------------------------------------------------------------
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
        description="Soft stop - zero velocities without changing robot state.",
        category="state",
        service="state_service",
        method="stop",
        requires_arm=False,
        response_format="Stopped",
    ),
    ToolDef(
        name="estop",
        description="Emergency stop - immediately halt all motion and enter ESTOP state. Requires clear_estop before resuming.",
        category="state",
        service="state_service",
        method="estop",
        requires_arm=False,
        response_format="E-STOP activated",
    ),
    ToolDef(
        name="clear_estop",
        description="Clear emergency stop condition (ESTOP -> IDLE). Required after estop before normal operation.",
        category="state",
        service="state_service",
        method="clear_estop",
        requires_arm=False,
        response_format="E-STOP cleared",
    ),
    ToolDef(
        name="activate",
        description="Activate the robot (ARMED -> ACTIVE). Motion commands are only accepted in ACTIVE state.",
        category="state",
        service="state_service",
        method="activate",
        requires_arm=False,
        response_format="Activated",
    ),
    ToolDef(
        name="deactivate",
        description="Deactivate the robot (ACTIVE -> ARMED). Stops accepting motion commands.",
        category="state",
        service="state_service",
        method="deactivate",
        requires_arm=False,
        response_format="Deactivated",
    ),
    ToolDef(
        name="get_robot_state",
        description="Query current robot state from MCU. Returns mode (IDLE/ARMED/ACTIVE/ESTOP), armed status, active status, and estop status.",
        category="state",
        service="state_service",
        method="get_state",
        requires_arm=False,
    ),

    # -------------------------------------------------------------------------
    # Motion Convenience Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="set_velocity",
        description="Set robot body velocity for differential drive. Uses reliable transport with ACK.",
        category="motion",
        service="motion_service",
        method="set_velocity_reliable",
        params=(
            ToolParam("vx", "number", "Linear velocity in m/s (positive = forward)"),
            ToolParam("omega", "number", "Angular velocity in rad/s (positive = counter-clockwise)"),
        ),
        response_format="Velocity set: vx={vx:.2f} m/s, omega={omega:.2f} rad/s",
    ),
    ToolDef(
        name="motion_forward",
        description="Move robot forward at specified speed.",
        category="motion",
        service="motion_service",
        method="forward",
        params=(
            ToolParam("speed", "number", "Speed (0.0 to 1.0)", required=False, default=0.5),
        ),
        response_format="Moving forward at {speed:.0%}",
    ),
    ToolDef(
        name="motion_backward",
        description="Move robot backward at specified speed.",
        category="motion",
        service="motion_service",
        method="backward",
        params=(
            ToolParam("speed", "number", "Speed (0.0 to 1.0)", required=False, default=0.5),
        ),
        response_format="Moving backward at {speed:.0%}",
    ),
    ToolDef(
        name="motion_rotate_left",
        description="Rotate robot counter-clockwise (left) at specified speed.",
        category="motion",
        service="motion_service",
        method="rotate_left",
        params=(
            ToolParam("speed", "number", "Rotation speed (0.0 to 1.0)", required=False, default=0.5),
        ),
        response_format="Rotating left at {speed:.0%}",
    ),
    ToolDef(
        name="motion_rotate_right",
        description="Rotate robot clockwise (right) at specified speed.",
        category="motion",
        service="motion_service",
        method="rotate_right",
        params=(
            ToolParam("speed", "number", "Rotation speed (0.0 to 1.0)", required=False, default=0.5),
        ),
        response_format="Rotating right at {speed:.0%}",
    ),

    # -------------------------------------------------------------------------
    # Servo Convenience Tools
    # -------------------------------------------------------------------------
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
        name="servo_sweep",
        description="Sweep a servo through a range of angles.",
        category="servo",
        service="servo_service",
        method="sweep",
        params=(
            ToolParam("servo_id", "integer", "Servo ID (0-7)"),
            ToolParam("start", "number", "Start angle in degrees", required=False, default=0),
            ToolParam("end", "number", "End angle in degrees", required=False, default=180),
            ToolParam("step", "number", "Step size in degrees", required=False, default=10),
            ToolParam("delay_s", "number", "Delay between steps in seconds", required=False, default=0.1),
        ),
        response_format="Servo {servo_id} sweep complete",
    ),
    ToolDef(
        name="servo_detach_all",
        description="Detach all servos from their pins.",
        category="servo",
        service="servo_service",
        method="detach_all",
        response_format="All servos detached",
    ),
    ToolDef(
        name="servo_list",
        description="List all attached servos.",
        category="servo",
        service="servo_service",
        method="get_attached_servos",
        requires_arm=False,
    ),

    # -------------------------------------------------------------------------
    # Motor Convenience Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="motor_brake",
        description="Apply active brake to a DC motor (shorts windings).",
        category="motor",
        service="motor_service",
        method="brake",
        params=(
            ToolParam("motor_id", "integer", "Motor ID (0-3)"),
        ),
        response_format="Motor {motor_id} braking",
    ),
    ToolDef(
        name="motor_stop_all",
        description="Stop all DC motors.",
        category="motor",
        service="motor_service",
        method="stop_all",
        response_format="All motors stopped",
    ),
    ToolDef(
        name="motor_set_differential",
        description="Set differential drive motor speeds for coordinated motion.",
        category="motor",
        service="motor_service",
        method="set_differential_drive",
        params=(
            ToolParam("left_speed", "number", "Left motor speed (-1.0 to 1.0)"),
            ToolParam("right_speed", "number", "Right motor speed (-1.0 to 1.0)"),
            ToolParam("left_motor", "integer", "Left motor ID", required=False, default=0),
            ToolParam("right_motor", "integer", "Right motor ID", required=False, default=1),
        ),
        response_format="Differential drive: L={left_speed:.0%}, R={right_speed:.0%}",
    ),
    ToolDef(
        name="motor_set_percent",
        description="Set DC motor speed as a percentage (0-100).",
        category="motor",
        service="motor_service",
        method="set_speed_percent",
        params=(
            ToolParam("motor_id", "integer", "Motor ID (0-3)"),
            ToolParam("percent", "number", "Speed percentage (0-100)"),
            ToolParam("clamp", "boolean", "Clamp to valid range", required=False, default=True),
        ),
        response_format="Motor {motor_id} -> {percent}%",
    ),

    # -------------------------------------------------------------------------
    # GPIO Convenience Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="gpio_list_channels",
        description="List all configured GPIO channels.",
        category="gpio",
        service="gpio_service",
        method="get_all_channels",
        requires_arm=False,
    ),

    # -------------------------------------------------------------------------
    # Signal Bus Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="signal_define",
        description="Define a new signal in the MCU signal bus. Signals enable data flow between control components.",
        category="signal",
        service="signal_service",
        method="define",
        params=(
            ToolParam("signal_id", "integer", "Signal ID (0-255)"),
            ToolParam("name", "string", "Signal name for identification"),
            ToolParam("kind", "string", "Signal kind: continuous, discrete, or event", required=False, default="continuous"),
            ToolParam("initial_value", "number", "Initial signal value", required=False, default=0.0),
        ),
        requires_arm=False,
        response_format="Signal {signal_id} ({name}) defined",
    ),
    ToolDef(
        name="signal_set",
        description="Set a signal value in the signal bus.",
        category="signal",
        service="signal_service",
        method="set",
        params=(
            ToolParam("signal_id", "integer", "Signal ID"),
            ToolParam("value", "number", "Value to set"),
        ),
        requires_arm=False,
        response_format="Signal {signal_id} = {value}",
    ),
    ToolDef(
        name="signal_get",
        description="Get a signal value from the MCU signal bus.",
        category="signal",
        service="signal_service",
        method="get",
        params=(
            ToolParam("signal_id", "integer", "Signal ID"),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="signal_list",
        description="List all defined signals in the signal bus.",
        category="signal",
        service="signal_service",
        method="list",
        requires_arm=False,
    ),
    ToolDef(
        name="signal_delete",
        description="Delete a signal from the signal bus.",
        category="signal",
        service="signal_service",
        method="delete",
        params=(
            ToolParam("signal_id", "integer", "Signal ID to delete"),
        ),
        requires_arm=False,
        response_format="Signal {signal_id} deleted",
    ),
    ToolDef(
        name="signal_clear",
        description="Clear all signals from the signal bus.",
        category="signal",
        service="signal_service",
        method="clear",
        requires_arm=False,
        response_format="All signals cleared",
    ),

    # -------------------------------------------------------------------------
    # Control Graph Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="control_graph_upload",
        description="Validate and upload a runtime control graph without enabling it.",
        category="control-graph",
        service="control_graph_service",
        method="upload",
        params=(
            ToolParam("graph", "object", "Control-graph config object with schema_version and slots."),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="control_graph_apply",
        description="Validate, upload, and enable a runtime control graph in one call.",
        category="control-graph",
        service="control_graph_service",
        method="apply",
        params=(
            ToolParam("graph", "object", "Control-graph config object with schema_version and slots."),
            ToolParam("enable", "boolean", "Enable the uploaded graph after upload succeeds.", required=False, default=True),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="control_graph_status",
        description="Get current control-graph presence, enable state, schema version, and slot status.",
        category="control-graph",
        service="control_graph_service",
        method="status",
        requires_arm=False,
    ),
    ToolDef(
        name="control_graph_enable",
        description="Enable the currently uploaded control graph.",
        category="control-graph",
        service="control_graph_service",
        method="enable",
        requires_arm=False,
    ),
    ToolDef(
        name="control_graph_disable",
        description="Disable the currently uploaded control graph.",
        category="control-graph",
        service="control_graph_service",
        method="disable",
        requires_arm=False,
    ),
    ToolDef(
        name="control_graph_clear",
        description="Clear the currently uploaded control graph from the MCU runtime.",
        category="control-graph",
        service="control_graph_service",
        method="clear",
        requires_arm=False,
    ),

    # -------------------------------------------------------------------------
    # Robot Abstraction Tools
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Camera Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="camera_set_resolution",
        description="Set camera resolution. Available: QQVGA(160x120), QVGA(320x240), VGA(640x480), SVGA(800x600), XGA(1024x768), SXGA(1280x1024), UXGA(1600x1200).",
        category="camera",
        service="camera_control_service",
        method="set_resolution",
        params=(
            ToolParam("resolution", "integer", "Resolution frame size (0=QQVGA, 5=QVGA, 8=VGA, 9=SVGA, 10=XGA, 12=SXGA, 13=UXGA)"),
        ),
        requires_arm=False,
        response_format="Camera resolution set",
    ),
    ToolDef(
        name="camera_set_quality",
        description="Set camera JPEG compression quality. Lower values = higher quality, larger files.",
        category="camera",
        service="camera_control_service",
        method="set_quality",
        params=(
            ToolParam("quality", "integer", "Quality value (4-63, lower is better quality)"),
        ),
        requires_arm=False,
        response_format="Camera quality set to {quality}",
    ),
    ToolDef(
        name="camera_set_brightness",
        description="Set camera brightness level.",
        category="camera",
        service="camera_control_service",
        method="set_brightness",
        params=(
            ToolParam("brightness", "integer", "Brightness level (-2 to 2)"),
        ),
        requires_arm=False,
        response_format="Camera brightness set to {brightness}",
    ),
    ToolDef(
        name="camera_set_contrast",
        description="Set camera contrast level.",
        category="camera",
        service="camera_control_service",
        method="set_contrast",
        params=(
            ToolParam("contrast", "integer", "Contrast level (-2 to 2)"),
        ),
        requires_arm=False,
        response_format="Camera contrast set to {contrast}",
    ),
    ToolDef(
        name="camera_set_saturation",
        description="Set camera color saturation level.",
        category="camera",
        service="camera_control_service",
        method="set_saturation",
        params=(
            ToolParam("saturation", "integer", "Saturation level (-2 to 2)"),
        ),
        requires_arm=False,
        response_format="Camera saturation set to {saturation}",
    ),
    ToolDef(
        name="camera_set_flip",
        description="Set camera image flip/mirror settings.",
        category="camera",
        service="camera_control_service",
        method="set_flip",
        params=(
            ToolParam("hmirror", "boolean", "Horizontal mirror", required=False, default=None),
            ToolParam("vflip", "boolean", "Vertical flip", required=False, default=None),
        ),
        requires_arm=False,
        response_format="Camera flip settings updated",
    ),
    ToolDef(
        name="camera_flash",
        description="Control camera flash LED.",
        category="camera",
        service="camera_control_service",
        method="set_flash",
        params=(
            ToolParam("state", "string", "Flash state: on, off, or toggle"),
        ),
        requires_arm=False,
        response_format="Camera flash {state}",
    ),
    ToolDef(
        name="camera_apply_preset",
        description="Apply a camera configuration preset. Presets: default, streaming, high_quality, fast, night, ml_inference.",
        category="camera",
        service="camera_control_service",
        method="apply_preset",
        params=(
            ToolParam("preset", "string", "Preset name: default, streaming, high_quality, fast, night, ml_inference"),
        ),
        requires_arm=False,
        response_format="Applied camera preset: {preset}",
    ),
    ToolDef(
        name="camera_get_status",
        description="Get current camera status and settings.",
        category="camera",
        service="camera_control_service",
        method="get_status",
        requires_arm=False,
    ),

    # -------------------------------------------------------------------------
    # Telemetry Tools
    # -------------------------------------------------------------------------
    ToolDef(
        name="telem_set_interval",
        description="Set telemetry publish interval in milliseconds. Set to 0 to disable.",
        category="telemetry",
        client_method="send_json_cmd",
        params=(
            ToolParam("interval_ms", "integer", "Telemetry interval in milliseconds (0 = disable)"),
        ),
        requires_arm=False,
    ),
    ToolDef(
        name="telem_set_rate",
        description="Set telemetry loop rate in Hz. Only allowed when IDLE.",
        category="telemetry",
        client_method="send_json_cmd",
        params=(
            ToolParam("hz", "integer", "Telemetry frequency in Hz (1-50)"),
        ),
        requires_arm=False,
    ),
]

# Combine host tools and service tools
HOST_TOOLS = HOST_TOOLS + SERVICE_TOOLS

# Legacy alias for backwards compatibility - generator uses HOST_TOOLS
TOOLS = HOST_TOOLS


# =============================================================================
# Helper Functions
# =============================================================================

def get_tools_by_category(category: str) -> list[ToolDef]:
    """Get all host tools in a category."""
    return [t for t in HOST_TOOLS if t.category == category]


def get_tool_by_name(name: str) -> ToolDef | None:
    """Get a host tool by name."""
    for t in HOST_TOOLS:
        if t.name == name:
            return t
    return None


def get_all_categories() -> list[str]:
    """Get list of all host tool categories."""
    return sorted(set(t.category for t in HOST_TOOLS))
