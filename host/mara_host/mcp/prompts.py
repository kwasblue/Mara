# mara_host/mcp/prompts.py
"""
MCP Prompts for MARA robot.

Prompts are predefined workflow templates that guide the LLM through
common operations. They embed domain knowledge so the LLM doesn't have
to reason about the right sequence of operations.
"""

from __future__ import annotations


# Prompt definitions
PROMPTS = {
    "startup": {
        "name": "startup",
        "description": "Connect to robot and prepare for operation",
        "arguments": [],
        "template": """Connect to the robot and prepare it for operation.

Steps:
1. Call mara_connect() to establish connection
2. Call mara_get_state() to verify connection and check current state
3. If state is IDLE, call mara_arm() to enable actuators
4. Call mara_get_health() to verify all systems are healthy
5. Report the robot's current state and available capabilities

If any step fails, report the error and suggested recovery action.""",
    },

    "shutdown": {
        "name": "shutdown",
        "description": "Safely shut down robot and disconnect",
        "arguments": [],
        "template": """Safely shut down the robot.

Steps:
1. Call mara_stop() to halt all motion
2. Call mara_deactivate() if in ACTIVE state
3. Call mara_disarm() to disable actuators
4. Call mara_disconnect() to close connection
5. Confirm shutdown complete

If any step fails, report the error but continue with remaining steps.""",
    },

    "diagnose": {
        "name": "diagnose",
        "description": "Diagnose robot health and connectivity issues",
        "arguments": [],
        "template": """Diagnose the robot's health and connectivity.

Steps:
1. Call mara_get_health() for overall health report
2. Call mara_get_freshness() to check data staleness
3. Call mara_get_snapshot() for detailed state
4. Check for:
   - Connection status (connected/disconnected)
   - Robot state (IDLE/ARMED/ACTIVE)
   - Telemetry freshness (stale data indicates issues)
   - Recent command failures
   - Recent error events

Report findings with:
- Overall status (healthy/degraded/unhealthy)
- Specific issues found
- Recommended actions to resolve issues""",
    },

    "test_motion": {
        "name": "test_motion",
        "description": "Test robot motion capabilities",
        "arguments": [],
        "template": """Test the robot's motion capabilities.

Prerequisites:
- Robot must be connected and armed
- If not, call mara_arm() first

Steps:
1. Call mara_activate() to enable motion control
2. Test forward motion: mara_motion_forward(duration_ms=500)
3. Wait 1 second
4. Test backward motion: mara_motion_backward(duration_ms=500)
5. Wait 1 second
6. Test rotation: mara_motion_rotate_left(duration_ms=500)
7. Call mara_stop() to ensure stopped
8. Call mara_deactivate() to exit active mode

Report results for each motion test.""",
    },

    "test_servos": {
        "name": "test_servos",
        "description": "Test servo motors by sweeping through range",
        "arguments": [
            {"name": "servo_id", "description": "Servo ID to test (default: 0)", "required": False},
        ],
        "template": """Test servo motor by sweeping through its range.

Prerequisites:
- Robot must be connected and armed
- If not, call mara_arm() first

Steps:
1. Get current servo position (if available)
2. Sweep to minimum angle: mara_servo_set(id={servo_id}, angle=0)
3. Wait 1 second
4. Sweep to center: mara_servo_set(id={servo_id}, angle=90)
5. Wait 1 second
6. Sweep to maximum: mara_servo_set(id={servo_id}, angle=180)
7. Wait 1 second
8. Return to center: mara_servo_set(id={servo_id}, angle=90)

Report success/failure for each position.""",
    },

    "upload_pid": {
        "name": "upload_pid",
        "description": "Upload a PID control graph for closed-loop control",
        "arguments": [
            {"name": "signal_in", "description": "Input signal ID (sensor feedback)", "required": True},
            {"name": "signal_out", "description": "Output signal ID (actuator command)", "required": True},
            {"name": "setpoint", "description": "Target setpoint value", "required": True},
            {"name": "kp", "description": "Proportional gain", "required": True},
            {"name": "ki", "description": "Integral gain (default: 0)", "required": False},
            {"name": "kd", "description": "Derivative gain (default: 0)", "required": False},
        ],
        "template": """Upload a PID control graph to the robot.

Prerequisites:
- Robot must be connected and armed
- If not, call mara_arm() first

Steps:
1. Verify robot is armed with mara_get_state()
2. Build control graph with PID slot:
   - Source: signal_read from {signal_in}
   - Transform: error (setpoint={setpoint})
   - Transform: scale (kp={kp})
   - Optional: integrator (ki={ki}) if ki > 0
   - Optional: derivative (kd={kd}) if kd > 0
   - Sink: signal_write to {signal_out}
3. Upload with mara_control_graph_upload()
4. Verify with mara_control_graph_status()

Report upload success and graph status.""",
    },

    "monitor_sensors": {
        "name": "monitor_sensors",
        "description": "Monitor sensor readings in real-time",
        "arguments": [
            {"name": "duration_s", "description": "How long to monitor (default: 10)", "required": False},
            {"name": "sensors", "description": "Which sensors: imu, encoder, all (default: all)", "required": False},
        ],
        "template": """Monitor sensor readings from the robot.

Prerequisites:
- Robot must be connected

Steps:
1. Check connection with mara_get_state()
2. For {duration_s} seconds (default 10):
   - If monitoring IMU: call mara_imu_read()
   - If monitoring encoder: call mara_encoder_read()
   - Report readings with timestamps
   - Wait 500ms between readings
3. Summarize observations (min, max, average values)

Report any anomalies detected (sudden changes, stuck values, noise).""",
    },
}


def get_prompt_definitions() -> list[dict]:
    """
    Get list of available MCP prompts.

    Returns prompt metadata for the MCP protocol.
    """
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "arguments": p.get("arguments", []),
        }
        for p in PROMPTS.values()
    ]


def get_prompt_template(name: str, arguments: dict | None = None) -> str | None:
    """
    Get a prompt template with arguments filled in.

    Args:
        name: Prompt name
        arguments: Optional arguments to fill in template

    Returns:
        Filled template string, or None if prompt not found
    """
    prompt = PROMPTS.get(name)
    if not prompt:
        return None

    template = prompt["template"]

    # Fill in arguments with defaults
    args = arguments or {}
    for arg_def in prompt.get("arguments", []):
        arg_name = arg_def["name"]
        if arg_name not in args:
            # Use default from description if mentioned
            if "default:" in arg_def["description"].lower():
                # Extract default value
                desc = arg_def["description"]
                default_start = desc.lower().find("default:")
                default_val = desc[default_start + 8:].strip().rstrip(")")
                args[arg_name] = default_val
            elif not arg_def.get("required", True):
                args[arg_name] = "0"  # Generic default

    # Simple template substitution
    for key, value in args.items():
        template = template.replace(f"{{{key}}}", str(value))

    return template
