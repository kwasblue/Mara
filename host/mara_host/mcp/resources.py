# mara_host/mcp/resources.py
"""
MCP Resources for MARA robot.

Resources provide passive context that the LLM can read without consuming
tool call budget. Many LLM clients automatically include resources in context.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .runtime import MaraRuntime


# Resource URIs
RESOURCE_STATE = "mara://robot/state"
RESOURCE_CAPABILITIES = "mara://robot/capabilities"
RESOURCE_SIGNALS = "mara://robot/signals"
RESOURCE_EVENTS = "mara://robot/events"
RESOURCE_COMMANDS = "mara://robot/commands"
RESOURCE_TOOLS = "mara://robot/tools"


def get_resource_definitions() -> list[dict]:
    """
    Get list of available MCP resources.

    These are exposed to the LLM for passive context reading.
    """
    return [
        {
            "uri": RESOURCE_STATE,
            "name": "Robot State",
            "description": "Current robot state, connection status, mode (IDLE/ARMED/ACTIVE), and telemetry freshness",
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_CAPABILITIES,
            "name": "Robot Capabilities",
            "description": "What this robot can do - available joints, sensors, actuators, and features",
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_SIGNALS,
            "name": "Signal Bus",
            "description": "Live sensor readings from IMU, encoders, motors via auto-signals",
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_EVENTS,
            "name": "Event Log",
            "description": "Recent state changes, command history, and errors",
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_COMMANDS,
            "name": "Command History",
            "description": "Recent commands with success/failure status and latency",
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_TOOLS,
            "name": "Tool Categories",
            "description": "Available tools organized by category - use to find the right tool for a task",
            "mimeType": "application/json",
        },
    ]


async def read_resource(runtime: "MaraRuntime", uri: str) -> str:
    """
    Read a resource and return its content as JSON.

    Args:
        runtime: The MaraRuntime instance
        uri: Resource URI to read

    Returns:
        JSON string with resource content
    """
    if uri == RESOURCE_STATE:
        return _read_state(runtime)
    elif uri == RESOURCE_CAPABILITIES:
        return await _read_capabilities(runtime)
    elif uri == RESOURCE_SIGNALS:
        return await _read_signals(runtime)
    elif uri == RESOURCE_EVENTS:
        return _read_events(runtime)
    elif uri == RESOURCE_COMMANDS:
        return _read_commands(runtime)
    elif uri == RESOURCE_TOOLS:
        return _read_tools()
    else:
        return json.dumps({"error": f"Unknown resource: {uri}"})


def _read_state(runtime: "MaraRuntime") -> str:
    """Read current robot state."""
    store = runtime.state

    state = {
        "connected": store.connected,
        "robot_state": {
            "value": store.robot_state.value,
            "freshness": store.robot_state.freshness,
            "age_s": round(store.robot_state.age_s, 2),
        },
        "firmware_version": store.firmware_version,
        "protocol_version": store.protocol_version,
        "features": store.features,
        "telemetry": {
            "imu": {
                "has_data": store.imu.value is not None,
                "freshness": store.imu.freshness,
            },
            "encoders": {
                eid: {"freshness": ev.freshness}
                for eid, ev in store.encoders.items()
            },
        },
    }

    if store.connected_at:
        state["connected_at"] = store.connected_at.isoformat()

    return json.dumps(state, indent=2)


async def _read_capabilities(runtime: "MaraRuntime") -> str:
    """Read robot capabilities."""
    caps = {
        "connected": runtime.is_connected,
        "features": list(runtime.state.features) if runtime.state.features else [],
    }

    # Add robot model info if loaded
    if runtime.robot_loaded:
        model = runtime.robot_model
        caps["robot"] = {
            "name": model.name,
            "type": model.type,
            "joints": list(model.joints.keys()),
            "joint_details": {
                name: {
                    "type": joint.type,
                    "limits": {"min": joint.min_angle, "max": joint.max_angle}
                    if hasattr(joint, "min_angle") else None,
                }
                for name, joint in model.joints.items()
            },
        }

    # Add feature capabilities
    features = runtime.state.features or []
    caps["available"] = {
        "imu": "IMU" in features,
        "encoder": "ENCODER" in features,
        "stepper": "STEPPER" in features,
        "servo": any("SERVO" in f or "PWM" in f for f in features),
        "wifi": "WIFI" in features,
        "dc_motor": "DC_MOTOR" in features or "MOTOR" in features,
        "control_graph": True,  # Always available
        "signals": True,  # Always available
    }

    return json.dumps(caps, indent=2)


async def _read_signals(runtime: "MaraRuntime") -> str:
    """Read signal bus state."""
    signals = {
        "available": runtime.is_connected,
    }

    if runtime.is_connected:
        try:
            # Get signal list from signal service
            result = await runtime.signal_service.list()
            if result.ok:
                signals["signals"] = result.signals
                signals["count"] = len(result.signals)
        except Exception as e:
            signals["error"] = str(e)

        # Also include cached IMU/encoder data
        store = runtime.state
        signals["cached"] = {
            "imu": store.imu.value if store.imu.value else None,
            "encoders": {
                eid: ev.value for eid, ev in store.encoders.items()
            },
        }

    return json.dumps(signals, indent=2)


def _read_events(runtime: "MaraRuntime") -> str:
    """Read recent events."""
    store = runtime.state
    events = [e.to_dict() for e in store.get_recent_events(20)]

    return json.dumps({
        "count": len(events),
        "events": events,
    }, indent=2)


def _read_commands(runtime: "MaraRuntime") -> str:
    """Read command history."""
    store = runtime.state
    commands = [c.to_dict() for c in store.commands[-20:]]
    stats = store.get_command_stats()

    return json.dumps({
        "stats": stats,
        "recent": commands,
    }, indent=2)


def _read_tools() -> str:
    """Read available tools organized by category."""
    from mara_host.mcp._generated_tools import get_tool_definitions
    from mara_host.mcp.categories import (
        list_tools_by_category,
        CATEGORIES,
    )

    all_tools = get_tool_definitions()
    by_cat = list_tools_by_category(all_tools)

    categories = {}
    for cat_id, cat in CATEGORIES.items():
        tools_in_cat = by_cat.get(cat_id, [])
        if tools_in_cat:
            categories[cat_id] = {
                "name": cat.name,
                "icon": cat.icon,
                "description": cat.description,
                "tools": [
                    {"name": t["name"], "description": t["description"]}
                    for t in sorted(tools_in_cat, key=lambda x: x["name"])
                ],
            }

    return json.dumps({
        "total_tools": len(all_tools),
        "categories": categories,
        "usage_hint": "Use mara_list_tools(category='motion') to see tools in a specific category",
    }, indent=2)
