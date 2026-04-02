"""
Host-side tool handlers for MCP.

These tools don't interact with firmware commands directly.
They handle host-side functionality like:
- Connection management
- State queries
- Recording sessions
- Testing
- Robot abstraction layer
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mara_host.mcp.runtime import MaraRuntime


# =============================================================================
# Connection Tools
# =============================================================================

async def handle_connect(runtime: "MaraRuntime", args: dict) -> str:
    """Connect to the robot."""
    result = await runtime.connect()
    return f"Connected: {result}"


async def handle_disconnect(runtime: "MaraRuntime", args: dict) -> str:
    """Disconnect from the robot."""
    result = await runtime.disconnect()
    return f"Disconnected: {result}"


# =============================================================================
# State Query Tools
# =============================================================================

async def handle_get_state(runtime: "MaraRuntime", args: dict) -> str:
    """Get current robot state snapshot."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.get_snapshot())


async def handle_get_freshness(runtime: "MaraRuntime", args: dict) -> str:
    """Get state freshness report."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.get_freshness_report())


async def handle_get_events(runtime: "MaraRuntime", args: dict) -> str:
    """Get recent events."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    events = runtime.state.get_recent_events(20)
    return str([e.to_dict() for e in events])


async def handle_get_command_stats(runtime: "MaraRuntime", args: dict) -> str:
    """Get command statistics."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."
    return str(runtime.state.get_command_stats())


# =============================================================================
# Robot Abstraction Layer Tools
# =============================================================================

async def handle_robot_describe(runtime: "MaraRuntime", args: dict) -> str:
    """Describe the loaded robot model."""
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_service.describe()


async def handle_robot_state(runtime: "MaraRuntime", args: dict) -> str:
    """Get robot state summary."""
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_context.get_state_summary()


async def handle_robot_pose(runtime: "MaraRuntime", args: dict) -> str:
    """Get robot pose."""
    if not runtime.robot_loaded:
        return "Robot not loaded. Call load_robot(config_path) first."
    return runtime.robot_context.format_pose()


# =============================================================================
# Testing Tools
# =============================================================================

async def handle_firmware_test(runtime: "MaraRuntime", args: dict) -> str:
    """Run firmware tests."""
    from mara_host.services import FirmwareTestService

    envs_str = args.get("environments", "native")
    environments = [e.strip() for e in envs_str.split(",")]
    filter_pattern = args.get("filter")
    verbose = args.get("verbose", False)

    service = FirmwareTestService()
    result = service.run_tests(
        environments=environments,
        filter_pattern=filter_pattern,
        verbose=verbose,
    )

    if result.ok:
        test_result = result.data.get("result") if result.data else None
        if test_result and test_result.output:
            return f"All tests passed\n{test_result.output}"
        return "All tests passed"
    return f"FAIL: {result.error}"


async def handle_host_test(runtime: "MaraRuntime", args: dict) -> str:
    """Run host Python tests."""
    import subprocess
    import sys
    from pathlib import Path

    filter_expr = args.get("filter")
    markers = args.get("markers")
    verbose = args.get("verbose", False)
    timeout = args.get("timeout", 300)

    host_dir = Path(__file__).parent.parent

    cmd = [sys.executable, "-m", "pytest"]
    if filter_expr:
        cmd.append(filter_expr)
    if markers:
        cmd.extend(["-m", markers])
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(
            cmd,
            cwd=host_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"All tests passed\n{output}"
        return f"FAIL: Tests failed (exit code {result.returncode})\n{output}"
    except subprocess.TimeoutExpired:
        return f"FAIL: Test timeout after {timeout}s"
    except Exception as e:
        return f"FAIL: {e}"


async def handle_robot_test_connection(runtime: "MaraRuntime", args: dict) -> str:
    """Test robot connection with ping."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."

    import asyncio

    start = datetime.now()
    try:
        ok, error = await asyncio.wait_for(
            runtime.client.send_reliable("CMD_HEARTBEAT", {}),
            timeout=1.0
        )
        duration = (datetime.now() - start).total_seconds() * 1000

        if ok:
            return f"Connection OK: ping {duration:.1f}ms"
        return f"FAIL: {error}"
    except asyncio.TimeoutError:
        return "FAIL: Timeout after 1000ms"


async def handle_robot_test_latency(runtime: "MaraRuntime", args: dict) -> str:
    """Test robot connection latency."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."

    import asyncio

    samples = args.get("samples", 10)
    latencies = []

    for _ in range(samples):
        start = datetime.now()
        try:
            await runtime.client.send_reliable("CMD_HEARTBEAT", {})
            latency = (datetime.now() - start).total_seconds() * 1000
            latencies.append(latency)
        except Exception:
            pass

    if not latencies:
        return "FAIL: No successful pings"

    avg = sum(latencies) / len(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)

    return f"Latency: avg={avg:.1f}ms, min={min_lat:.1f}ms, max={max_lat:.1f}ms ({len(latencies)}/{samples} samples)"


async def handle_robot_test_all(runtime: "MaraRuntime", args: dict) -> str:
    """Run all robot connection tests."""
    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."

    results = []

    # Test connection
    conn_result = await handle_robot_test_connection(runtime, {})
    results.append(f"Connection: {conn_result}")

    # Test latency
    lat_result = await handle_robot_test_latency(runtime, {"samples": 5})
    results.append(f"Latency: {lat_result}")

    return "\n".join(results)


# =============================================================================
# Recording Tools
# =============================================================================

async def handle_record_start(runtime: "MaraRuntime", args: dict) -> str:
    """Start recording telemetry."""
    from pathlib import Path
    from mara_host.services.recording.recording_service import RecordingService, RecordingConfig

    if not runtime.is_connected:
        return "Not connected. Use mara_connect first."

    # Check if already recording
    if hasattr(runtime, '_recording_service') and runtime._recording_service is not None:
        return "Already recording. Stop the current recording first."

    session_name = args.get("session_name") or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    config = RecordingConfig(
        session_name=session_name,
        log_dir=Path("logs"),
    )

    recording_service = RecordingService(config)
    session_path = await recording_service.start()

    # Store on runtime for later access
    runtime._recording_service = recording_service

    return f"Recording started: {session_name} -> {session_path}"


async def handle_record_stop(runtime: "MaraRuntime", args: dict) -> str:
    """Stop recording telemetry."""
    if not hasattr(runtime, '_recording_service') or runtime._recording_service is None:
        return "No recording in progress."

    session_info = await runtime._recording_service.stop()
    runtime._recording_service = None

    return f"Recording stopped: {session_info.name} ({session_info.event_count} events, {session_info.duration_s:.1f}s)"


async def handle_record_list(runtime: "MaraRuntime", args: dict) -> str:
    """List recording sessions."""
    from pathlib import Path
    from mara_host.services.recording.recording_service import ReplayService

    sessions = ReplayService.list_sessions(Path("logs"))

    if not sessions:
        return "No recording sessions found."

    return f"Recording sessions ({len(sessions)}): " + ", ".join(sessions)


async def handle_record_status(runtime: "MaraRuntime", args: dict) -> str:
    """Get current recording status."""
    if not hasattr(runtime, '_recording_service') or runtime._recording_service is None:
        return "Not recording."

    service = runtime._recording_service
    return f"Recording: {service.config.session_name} -> {service.session_path}"


# =============================================================================
# Handler Registry
# =============================================================================

HOST_TOOL_HANDLERS = {
    # Connection
    "connect": handle_connect,
    "disconnect": handle_disconnect,
    # State
    "get_state": handle_get_state,
    "get_freshness": handle_get_freshness,
    "get_events": handle_get_events,
    "get_command_stats": handle_get_command_stats,
    # Robot abstraction
    "robot_describe": handle_robot_describe,
    "robot_state": handle_robot_state,
    "robot_pose": handle_robot_pose,
    # Testing
    "firmware_test": handle_firmware_test,
    "host_test": handle_host_test,
    "robot_test_connection": handle_robot_test_connection,
    "robot_test_latency": handle_robot_test_latency,
    "robot_test_all": handle_robot_test_all,
    # Recording
    "record_start": handle_record_start,
    "record_stop": handle_record_stop,
    "record_list": handle_record_list,
    "record_status": handle_record_status,
}


async def dispatch_host_tool(runtime: "MaraRuntime", name: str, args: dict) -> str | None:
    """
    Dispatch a host tool by name.

    Args:
        runtime: MCP runtime
        name: Tool name (without mara_ prefix)
        args: Tool arguments

    Returns:
        Result string, or None if not a host tool
    """
    handler = HOST_TOOL_HANDLERS.get(name)
    if handler:
        return await handler(runtime, args)
    return None
