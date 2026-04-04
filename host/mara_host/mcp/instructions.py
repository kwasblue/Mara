# mara_host/mcp/instructions.py
"""
MCP server instructions for LLM guidance.

These instructions are injected into the LLM's context when the MCP server
starts, providing critical guidance on how to interact with the robot.
"""

# Server-level instructions that get injected into LLM context
SERVER_INSTRUCTIONS = """You are controlling a MARA robot via MCP tools.

CRITICAL RULES:
1. NEVER use subprocess, shell commands, or CLI invocations (like `mara arm` or `python -m mara_host`).
   All robot control MUST go through the mara_* tools provided here.
   The CLI is not available in this context and would fail silently.

2. ALWAYS start by calling mara_get_state to understand current robot status.

3. The robot has a state machine: IDLE -> ARMED -> ACTIVE
   - IDLE: Can query state, connect, read sensors
   - ARMED: Can configure actuators, upload control graphs
   - ACTIVE: Can send motion commands

4. Before actuator commands (motors, servos, motion), the robot MUST be armed.
   Call mara_arm() first if state is IDLE.

5. If a command fails, check the error response for "next_action" - it tells you
   exactly what to do to recover.

6. Use mara_get_health to diagnose connection or hardware issues.

TOOL SELECTION GUIDANCE:
- For motion: Use mara_set_vel for continuous velocity, mara_motion_* for discrete moves
- For state: Use mara_get_state (current) or mara_get_snapshot (comprehensive)
- For sensors: Use mara_read_signals (auto-signals) or specific sensor tools
- For control: Use mara_upload_control_graph for PID loops and behaviors

When in doubt, call mara_get_state first to understand the robot's current situation.
"""

# Standard mode tool descriptions - enhanced with usage guidance
STANDARD_TOOL_GUIDANCE = {
    "mara_connect": "Connect to the robot. Call this first before any other commands.",
    "mara_disconnect": "Disconnect from the robot. Call when done.",
    "mara_arm": "Arm the robot for actuator commands. Required before motors/servos will respond.",
    "mara_disarm": "Disarm the robot. Actuators become unresponsive.",
    "mara_activate": "Activate the robot for motion commands. Required for velocity control.",
    "mara_deactivate": "Deactivate the robot. Stops motion control.",
    "mara_stop": "Stop all motion immediately but stay armed.",
    "mara_estop": "EMERGENCY STOP. Immediately halt all actuators and enter safe state.",
    "mara_get_state": "Get current robot state (IDLE/ARMED/ACTIVE). Call this first to understand status.",
    "mara_get_snapshot": "Get comprehensive state snapshot including sensors, commands, events. Use for diagnosis.",
    "mara_get_health": "Get health report for connection and hardware status. Use to diagnose issues.",
    "mara_set_vel": "Set velocity for continuous motion. Use for differential drive. Requires ACTIVE state.",
    "mara_motion_forward": "Move forward for specified duration. One-shot motion command.",
    "mara_motion_backward": "Move backward for specified duration. One-shot motion command.",
    "mara_motion_rotate_left": "Rotate left for specified duration. One-shot motion command.",
    "mara_motion_rotate_right": "Rotate right for specified duration. One-shot motion command.",
    "mara_servo_set": "Set servo angle. Requires ARMED state.",
    "mara_motor_set": "Set motor speed directly. Requires ARMED state.",
    "mara_upload_control_graph": "Upload a control graph for autonomous behavior. Requires ARMED state.",
    "mara_robot_describe": "Describe robot capabilities from configuration. Call to understand what's available.",
}

# Tools exposed in standard mode (curated ~20 tools)
STANDARD_MODE_TOOLS = {
    # Lifecycle
    "mara_connect",
    "mara_disconnect",
    # State management
    "mara_arm",
    "mara_disarm",
    "mara_activate",
    "mara_deactivate",
    "mara_stop",
    "mara_estop",
    "mara_clear_estop",
    # State queries
    "mara_get_state",
    "mara_get_robot_state",
    "mara_get_snapshot",
    "mara_get_health",
    "mara_get_freshness",
    "mara_get_identity",
    # Motion
    "mara_set_vel",
    "mara_set_velocity",
    "mara_motion_forward",
    "mara_motion_backward",
    "mara_motion_rotate_left",
    "mara_motion_rotate_right",
    # Actuators
    "mara_servo_set",
    "mara_servo_center",
    "mara_servo_detach",
    "mara_motor_set",
    "mara_motor_stop",
    "mara_motor_stop_all",
    # Sensors
    "mara_imu_read",
    "mara_encoder_read",
    "mara_ultrasonic_read",
    # Signals
    "mara_signal_get",
    "mara_signal_set",
    "mara_signal_list",
    # Control graph (simplified)
    "mara_control_graph_upload",
    "mara_control_graph_status",
    "mara_control_graph_clear",
    # Robot abstraction
    "mara_robot_describe",
    "mara_robot_state",
    "mara_robot_pose",
    "mara_robot_move",
    "mara_robot_home",
}


def get_mode_tools(mode: str) -> set[str] | None:
    """
    Get the set of tools to expose for a given mode.

    Args:
        mode: "standard" for curated tools, "developer" for all tools

    Returns:
        Set of tool names to expose, or None for all tools
    """
    if mode == "standard":
        return STANDARD_MODE_TOOLS
    return None  # Developer mode: expose all
