# mara_host/cli/commands/run/shell/commands/camera.py
"""Camera commands."""

from .registry import command
from mara_host.cli.console import console, print_success, print_error, print_info


@command("cam", "Camera: cam capture/stream/preset ...", group="Camera")
async def cmd_cam(shell, args: list[str]) -> None:
    """Camera commands."""
    if not args:
        console.print("Usage:")
        console.print("  cam capture                 Capture frame")
        console.print("  cam stream start/stop       Control streaming")
        console.print("  cam preset <name>           Apply preset")
        console.print("  cam flash on/off            Control flash")
        console.print("  cam resolution <w> <h>      Set resolution")
        return
    if not shell.require_connection():
        return

    action = args[0].lower()
    if action == "capture":
        await shell.client.send_reliable("CMD_CAM_CAPTURE_FRAME", {})
        print_info("Camera capture requested")
    elif action == "stream" and len(args) >= 2:
        if args[1].lower() == "start":
            await shell.client.send_reliable("CMD_CAM_STREAM_START", {})
            print_success("Camera streaming started")
        else:
            await shell.client.send_reliable("CMD_CAM_STREAM_STOP", {})
            print_success("Camera streaming stopped")
    elif action == "preset" and len(args) >= 2:
        preset = args[1]
        await shell.client.send_reliable("CMD_CAM_APPLY_PRESET", {"preset": preset})
        print_success(f"Camera preset '{preset}' applied")
    elif action == "flash" and len(args) >= 2:
        enable = args[1].lower() in ("on", "1", "true")
        await shell.client.send_reliable("CMD_CAM_FLASH", {"enable": enable})
        print_success(f"Camera flash {'on' if enable else 'off'}")
    elif action == "resolution" and len(args) >= 3:
        width = int(args[1])
        height = int(args[2])
        await shell.client.send_reliable("CMD_CAM_SET_RESOLUTION", {"width": width, "height": height})
        print_success(f"Camera resolution set to {width}x{height}")
    else:
        print_error(f"Unknown cam action: {args}")
