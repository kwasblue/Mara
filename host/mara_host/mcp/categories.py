# mara_host/mcp/categories.py
"""
Tool categorization for MCP tools.

Organizes tools into logical categories to help LLMs find the right tool.
Categories are prefixed to descriptions and can be queried via mara_list_tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCategory:
    """A category of tools."""
    id: str
    name: str
    description: str
    icon: str  # Emoji for visual distinction


# Category definitions
CATEGORIES = {
    "lifecycle": ToolCategory(
        id="lifecycle",
        name="Lifecycle",
        description="Connection and session management",
        icon="🔌",
    ),
    "state": ToolCategory(
        id="state",
        name="State",
        description="Robot state queries and mode changes (IDLE/ARMED/ACTIVE)",
        icon="📊",
    ),
    "safety": ToolCategory(
        id="safety",
        name="Safety",
        description="Emergency stop and safety controls",
        icon="🛑",
    ),
    "motion": ToolCategory(
        id="motion",
        name="Motion",
        description="Movement commands - velocity, direction, discrete moves",
        icon="🚗",
    ),
    "servo": ToolCategory(
        id="servo",
        name="Servo",
        description="Servo motor control - angles, sweep, detach",
        icon="🎯",
    ),
    "motor": ToolCategory(
        id="motor",
        name="Motor",
        description="DC and stepper motor control",
        icon="⚙️",
    ),
    "sensor": ToolCategory(
        id="sensor",
        name="Sensor",
        description="Sensor readings - IMU, encoders, ultrasonic, lidar",
        icon="📡",
    ),
    "signal": ToolCategory(
        id="signal",
        name="Signal",
        description="Signal bus - define, read, write signals",
        icon="📶",
    ),
    "control": ToolCategory(
        id="control",
        name="Control",
        description="Control graph - upload, configure, monitor control loops",
        icon="🎛️",
    ),
    "gpio": ToolCategory(
        id="gpio",
        name="GPIO",
        description="General purpose I/O - digital pins, PWM",
        icon="🔧",
    ),
    "config": ToolCategory(
        id="config",
        name="Config",
        description="Robot configuration and setup",
        icon="⚙️",
    ),
    "diagnostic": ToolCategory(
        id="diagnostic",
        name="Diagnostic",
        description="Testing, health checks, debugging",
        icon="🔍",
    ),
    "recording": ToolCategory(
        id="recording",
        name="Recording",
        description="Telemetry recording and playback",
        icon="🎬",
    ),
    "network": ToolCategory(
        id="network",
        name="Network",
        description="WiFi, Bluetooth, network configuration",
        icon="📡",
    ),
    "benchmark": ToolCategory(
        id="benchmark",
        name="Benchmark",
        description="Performance benchmarking",
        icon="📈",
    ),
    "camera": ToolCategory(
        id="camera",
        name="Camera",
        description="Camera control and settings",
        icon="📷",
    ),
}


# Tool to category mapping
TOOL_CATEGORIES: dict[str, str] = {
    # Lifecycle
    "mara_connect": "lifecycle",
    "mara_disconnect": "lifecycle",

    # State
    "mara_get_state": "state",
    "mara_get_snapshot": "state",
    "mara_get_robot_state": "state",
    "mara_get_freshness": "state",
    "mara_get_health": "state",
    "mara_get_events": "state",
    "mara_get_command_stats": "state",
    "mara_get_identity": "state",
    "mara_arm": "state",
    "mara_disarm": "state",
    "mara_activate": "state",
    "mara_deactivate": "state",

    # Safety
    "mara_stop": "safety",
    "mara_estop": "safety",
    "mara_clear_estop": "safety",
    "mara_motor_stop": "safety",
    "mara_motor_stop_all": "safety",

    # Motion
    "mara_set_vel": "motion",
    "mara_set_velocity": "motion",
    "mara_motion_forward": "motion",
    "mara_motion_backward": "motion",
    "mara_motion_rotate_left": "motion",
    "mara_motion_rotate_right": "motion",
    "mara_robot_move": "motion",
    "mara_robot_home": "motion",

    # Servo
    "mara_servo_set": "servo",
    "mara_servo_center": "servo",
    "mara_servo_attach": "servo",
    "mara_servo_detach": "servo",
    "mara_servo_detach_all": "servo",
    "mara_servo_list": "servo",
    "mara_servo_sweep": "servo",
    "mara_servo_set_pulse": "servo",

    # Motor (DC and stepper)
    "mara_motor_set": "motor",
    "mara_motor_set_percent": "motor",
    "mara_motor_set_differential": "motor",
    "mara_motor_brake": "motor",
    "mara_motor_set_vel_gains": "motor",
    "mara_motor_set_vel_target": "motor",
    "mara_motor_vel_pid_enable": "motor",
    "mara_stepper_enable": "motor",
    "mara_stepper_move": "motor",
    "mara_stepper_move_deg": "motor",
    "mara_stepper_move_rev": "motor",
    "mara_stepper_stop": "motor",
    "mara_stepper_get_position": "motor",
    "mara_stepper_reset_position": "motor",

    # Sensor
    "mara_imu_read": "sensor",
    "mara_imu_calibrate": "sensor",
    "mara_imu_zero": "sensor",
    "mara_imu_set_bias": "sensor",
    "mara_encoder_read": "sensor",
    "mara_encoder_attach": "sensor",
    "mara_encoder_detach": "sensor",
    "mara_encoder_reset": "sensor",
    "mara_ultrasonic_read": "sensor",
    "mara_ultrasonic_attach": "sensor",
    "mara_ultrasonic_detach": "sensor",

    # Signal
    "mara_signal_define": "signal",
    "mara_signal_get": "signal",
    "mara_signal_set": "signal",
    "mara_signal_list": "signal",
    "mara_signal_delete": "signal",
    "mara_signal_clear": "signal",
    "mara_ctrl_signal_define": "signal",
    "mara_ctrl_signal_get": "signal",
    "mara_ctrl_signal_set": "signal",
    "mara_ctrl_signal_delete": "signal",
    "mara_ctrl_signals_list": "signal",
    "mara_ctrl_signals_clear": "signal",

    # Control graph
    "mara_control_graph_upload": "control",
    "mara_control_graph_apply": "control",
    "mara_control_graph_status": "control",
    "mara_control_graph_clear": "control",
    "mara_control_graph_enable": "control",
    "mara_control_graph_disable": "control",
    "mara_ctrl_graph_upload": "control",
    "mara_ctrl_graph_clear": "control",
    "mara_ctrl_graph_enable": "control",
    "mara_ctrl_graph_status": "control",
    "mara_ctrl_slot_config": "control",
    "mara_ctrl_slot_enable": "control",
    "mara_ctrl_slot_status": "control",
    "mara_ctrl_slot_reset": "control",
    "mara_ctrl_slot_get_param": "control",
    "mara_ctrl_slot_set_param": "control",
    "mara_ctrl_slot_set_param_array": "control",
    "mara_observer_config": "control",
    "mara_observer_enable": "control",
    "mara_observer_status": "control",
    "mara_observer_reset": "control",
    "mara_observer_set_param": "control",
    "mara_observer_set_param_array": "control",

    # GPIO
    "mara_gpio_register_channel": "gpio",
    "mara_gpio_read": "gpio",
    "mara_gpio_write": "gpio",
    "mara_gpio_toggle": "gpio",
    "mara_gpio_list_channels": "gpio",
    "mara_pwm_set": "gpio",
    "mara_led_on": "gpio",
    "mara_led_off": "gpio",

    # Config / Robot
    "mara_robot_describe": "config",
    "mara_robot_state": "config",
    "mara_robot_pose": "config",

    # Diagnostic
    "mara_get_health": "diagnostic",
    "mara_firmware_test": "diagnostic",
    "mara_host_test": "diagnostic",
    "mara_robot_test_connection": "diagnostic",
    "mara_robot_test_latency": "diagnostic",
    "mara_robot_test_all": "diagnostic",
    "mara_i2c_scan": "diagnostic",
    "mara_mcu_diagnostics_query": "diagnostic",
    "mara_mcu_diagnostics_reset": "diagnostic",
    "mara_perf_reset": "diagnostic",
    "mara_logging_log_level": "diagnostic",
    "mara_logging_log_levels": "diagnostic",
    "mara_logging_subsystem_log_level": "diagnostic",
    "mara_logging_subsystem_log_levels": "diagnostic",
    "mara_system_rates": "diagnostic",
    "mara_system_set_rate": "diagnostic",
    "mara_safety_safety_timeouts": "diagnostic",

    # Recording
    "mara_record_start": "recording",
    "mara_record_stop": "recording",
    "mara_record_list": "recording",
    "mara_record_status": "recording",

    # Network
    "mara_wifi_scan": "network",
    "mara_wifi_join": "network",
    "mara_wifi_status": "network",
    "mara_wifi_disconnect": "network",

    # Benchmark
    "mara_bench_start": "benchmark",
    "mara_bench_stop": "benchmark",
    "mara_bench_status": "benchmark",
    "mara_bench_list_tests": "benchmark",
    "mara_bench_run_boot_tests": "benchmark",
    "mara_bench_get_results": "benchmark",

    # Camera
    "mara_camera_get_status": "camera",
    "mara_camera_set_brightness": "camera",
    "mara_camera_set_contrast": "camera",
    "mara_camera_set_saturation": "camera",
    "mara_camera_set_quality": "camera",
    "mara_camera_set_resolution": "camera",
    "mara_camera_set_flip": "camera",
    "mara_camera_apply_preset": "camera",
    "mara_camera_flash": "camera",

    # Telemetry
    "mara_telem_set_interval": "diagnostic",
    "mara_telem_set_rate": "diagnostic",
    "mara_telemetry_set_interval": "diagnostic",

    # Batch
    "mara_batch_apply": "control",

    # Additional control tools
    "mara_ctrl_auto_signals_config": "signal",
    "mara_ctrl_graph_commit": "control",
    "mara_ctrl_graph_debug": "control",
    "mara_ctrl_signal_trace": "signal",
    "mara_set_mode": "state",
}


def get_tool_category(tool_name: str) -> ToolCategory | None:
    """Get the category for a tool."""
    cat_id = TOOL_CATEGORIES.get(tool_name)
    if cat_id:
        return CATEGORIES.get(cat_id)
    return None


def get_category_description(tool_name: str) -> str:
    """Get a category prefix for a tool description."""
    cat = get_tool_category(tool_name)
    if cat:
        return f"[{cat.name}] "
    return ""


def list_tools_by_category(tools: list[Any]) -> dict[str, list[dict]]:
    """
    Organize tools by category.

    Args:
        tools: List of Tool objects

    Returns:
        Dict mapping category ID to list of tool info dicts
    """
    by_category: dict[str, list[dict]] = {}

    for tool in tools:
        cat_id = TOOL_CATEGORIES.get(tool.name, "other")
        if cat_id not in by_category:
            by_category[cat_id] = []

        by_category[cat_id].append({
            "name": tool.name,
            "description": tool.description,
        })

    return by_category


def get_category_summary() -> dict[str, dict]:
    """
    Get a summary of all categories with tool counts.

    Returns:
        Dict mapping category ID to category info with count
    """
    # Count tools per category
    counts: dict[str, int] = {}
    for cat_id in TOOL_CATEGORIES.values():
        counts[cat_id] = counts.get(cat_id, 0) + 1

    return {
        cat_id: {
            "name": cat.name,
            "description": cat.description,
            "icon": cat.icon,
            "tool_count": counts.get(cat_id, 0),
        }
        for cat_id, cat in CATEGORIES.items()
    }


def format_tools_for_llm(tools: list[Any]) -> str:
    """
    Format tools organized by category for LLM consumption.

    Returns a markdown-formatted string showing tools by category.
    """
    by_cat = list_tools_by_category(tools)
    lines = ["# Available Tools by Category\n"]

    for cat_id, cat in CATEGORIES.items():
        if cat_id not in by_cat:
            continue

        cat_tools = by_cat[cat_id]
        lines.append(f"\n## {cat.icon} {cat.name} ({len(cat_tools)} tools)")
        lines.append(f"_{cat.description}_\n")

        for t in sorted(cat_tools, key=lambda x: x["name"]):
            lines.append(f"- **{t['name']}**: {t['description']}")

    # Handle uncategorized
    if "other" in by_cat:
        lines.append(f"\n## Other ({len(by_cat['other'])} tools)")
        for t in sorted(by_cat["other"], key=lambda x: x["name"]):
            lines.append(f"- **{t['name']}**: {t['description']}")

    return "\n".join(lines)
