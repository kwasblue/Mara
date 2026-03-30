# mara_host/cli/commands/camera.py
"""Camera control commands."""

import argparse

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.cli.context import CLIContext, run_with_context
from mara_host.cli.commands._common import add_port_arg, cmd_help


RESOLUTIONS = {
    "qqvga": (0, "160x120"),
    "qcif": (2, "176x144"),
    "hqvga": (3, "240x176"),
    "qvga": (5, "320x240"),
    "cif": (6, "400x296"),
    "vga": (8, "640x480"),
    "svga": (9, "800x600"),
    "xga": (10, "1024x768"),
    "sxga": (12, "1280x1024"),
    "uxga": (13, "1600x1200"),
}

PRESETS = ["default", "streaming", "high_quality", "fast", "night", "ml_inference"]


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register camera command group."""
    camera_parser = subparsers.add_parser(
        "camera",
        help="Camera control",
        description="Control ESP32-CAM camera settings",
        aliases=["cam"],
    )

    camera_sub = camera_parser.add_subparsers(
        dest="camera_cmd",
        title="camera commands",
        metavar="<subcommand>",
    )

    # camera status
    status_p = camera_sub.add_parser("status", help="Show camera status")
    add_port_arg(status_p)
    status_p.set_defaults(func=cmd_status)

    # camera resolution
    res_p = camera_sub.add_parser("resolution", help="Set camera resolution")
    res_p.add_argument(
        "resolution",
        choices=list(RESOLUTIONS.keys()),
        help="Resolution preset",
    )
    add_port_arg(res_p)
    res_p.set_defaults(func=cmd_resolution)

    # camera quality
    qual_p = camera_sub.add_parser("quality", help="Set JPEG quality (4-63, lower=better)")
    qual_p.add_argument("quality", type=int, help="Quality value (4-63)")
    add_port_arg(qual_p)
    qual_p.set_defaults(func=cmd_quality)

    # camera brightness
    bright_p = camera_sub.add_parser("brightness", help="Set brightness (-2 to 2)")
    bright_p.add_argument("level", type=int, help="Brightness level (-2 to 2)")
    add_port_arg(bright_p)
    bright_p.set_defaults(func=cmd_brightness)

    # camera contrast
    contrast_p = camera_sub.add_parser("contrast", help="Set contrast (-2 to 2)")
    contrast_p.add_argument("level", type=int, help="Contrast level (-2 to 2)")
    add_port_arg(contrast_p)
    contrast_p.set_defaults(func=cmd_contrast)

    # camera saturation
    sat_p = camera_sub.add_parser("saturation", help="Set saturation (-2 to 2)")
    sat_p.add_argument("level", type=int, help="Saturation level (-2 to 2)")
    add_port_arg(sat_p)
    sat_p.set_defaults(func=cmd_saturation)

    # camera flip
    flip_p = camera_sub.add_parser("flip", help="Set image flip/mirror")
    flip_p.add_argument("--hmirror", action="store_true", help="Horizontal mirror")
    flip_p.add_argument("--vflip", action="store_true", help="Vertical flip")
    flip_p.add_argument("--no-hmirror", action="store_true", help="Disable horizontal mirror")
    flip_p.add_argument("--no-vflip", action="store_true", help="Disable vertical flip")
    add_port_arg(flip_p)
    flip_p.set_defaults(func=cmd_flip)

    # camera flash
    flash_p = camera_sub.add_parser("flash", help="Control flash LED")
    flash_p.add_argument(
        "state",
        choices=["on", "off", "toggle"],
        help="Flash state",
    )
    add_port_arg(flash_p)
    flash_p.set_defaults(func=cmd_flash)

    # camera preset
    preset_p = camera_sub.add_parser("preset", help="Apply configuration preset")
    preset_p.add_argument(
        "preset",
        choices=PRESETS,
        help="Preset name",
    )
    add_port_arg(preset_p)
    preset_p.set_defaults(func=cmd_preset)

    # camera capture
    capture_p = camera_sub.add_parser("capture", help="Capture a single frame")
    add_port_arg(capture_p)
    capture_p.set_defaults(func=cmd_capture)

    # camera start
    start_p = camera_sub.add_parser("start", help="Start continuous capture")
    start_p.add_argument(
        "--fps",
        type=float,
        default=10.0,
        help="Target frame rate (default: 10)",
    )
    add_port_arg(start_p)
    start_p.set_defaults(func=cmd_start)

    # camera stop
    stop_p = camera_sub.add_parser("stop", help="Stop continuous capture")
    add_port_arg(stop_p)
    stop_p.set_defaults(func=cmd_stop)

    # camera list-resolutions
    list_res_p = camera_sub.add_parser(
        "list-resolutions", help="List available resolutions"
    )
    list_res_p.set_defaults(func=cmd_list_resolutions)

    # Default handler
    camera_parser.set_defaults(func=lambda args: cmd_help(camera_parser))


@run_with_context
async def cmd_status(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Get camera status."""
    ok, error, data = await ctx.client.send_with_data("CMD_CAM_GET_STATUS", {"camera_id": 0})

    if ok:
        data = data or {}
        table = Table(title="Camera Status", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Resolution", data.get("resolution", "unknown"))
        table.add_row("Quality", str(data.get("quality", "?")))
        table.add_row("Brightness", str(data.get("brightness", 0)))
        table.add_row("Contrast", str(data.get("contrast", 0)))
        table.add_row("Saturation", str(data.get("saturation", 0)))
        table.add_row("H-Mirror", "Yes" if data.get("hmirror") else "No")
        table.add_row("V-Flip", "Yes" if data.get("vflip") else "No")
        table.add_row("Capturing", "Yes" if data.get("capturing") else "No")

        console.print(table)
        return 0
    else:
        print_error(f"Failed to get status: {error}")
        return 1


@run_with_context
async def cmd_resolution(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set camera resolution."""
    res_value, res_dims = RESOLUTIONS[args.resolution]

    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_SET_RESOLUTION",
        {"camera_id": 0, "size": res_value},
    )

    if ok:
        print_success(f"Resolution set to {args.resolution.upper()} ({res_dims})")
        return 0
    else:
        print_error(f"Failed to set resolution: {error}")
        return 1


@run_with_context
async def cmd_quality(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set JPEG quality."""
    quality = max(4, min(63, args.quality))

    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_SET_QUALITY",
        {"camera_id": 0, "quality": quality},
    )

    if ok:
        print_success(f"Quality set to {quality}")
        return 0
    else:
        print_error(f"Failed to set quality: {error}")
        return 1


@run_with_context
async def cmd_brightness(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set brightness."""
    level = max(-2, min(2, args.level))

    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_SET_BRIGHTNESS",
        {"camera_id": 0, "brightness": level},
    )

    if ok:
        print_success(f"Brightness set to {level}")
        return 0
    else:
        print_error(f"Failed to set brightness: {error}")
        return 1


@run_with_context
async def cmd_contrast(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set contrast."""
    level = max(-2, min(2, args.level))

    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_SET_CONTRAST",
        {"camera_id": 0, "contrast": level},
    )

    if ok:
        print_success(f"Contrast set to {level}")
        return 0
    else:
        print_error(f"Failed to set contrast: {error}")
        return 1


@run_with_context
async def cmd_saturation(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set saturation."""
    level = max(-2, min(2, args.level))

    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_SET_SATURATION",
        {"camera_id": 0, "saturation": level},
    )

    if ok:
        print_success(f"Saturation set to {level}")
        return 0
    else:
        print_error(f"Failed to set saturation: {error}")
        return 1


@run_with_context
async def cmd_flip(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Set image flip/mirror."""
    payload = {"camera_id": 0}

    if args.hmirror:
        payload["hmirror"] = True
    elif args.no_hmirror:
        payload["hmirror"] = False

    if args.vflip:
        payload["vflip"] = True
    elif args.no_vflip:
        payload["vflip"] = False

    if len(payload) == 1:
        print_error("Specify at least one flip option (--hmirror, --vflip, --no-hmirror, --no-vflip)")
        return 1

    ok, error = await ctx.client.send_reliable("CMD_CAM_SET_FLIP", payload)

    if ok:
        print_success("Flip settings updated")
        return 0
    else:
        print_error(f"Failed to set flip: {error}")
        return 1


@run_with_context
async def cmd_flash(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Control flash LED."""
    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_FLASH",
        {"camera_id": 0, "state": args.state},
    )

    if ok:
        print_success(f"Flash {args.state}")
        return 0
    else:
        print_error(f"Failed to control flash: {error}")
        return 1


@run_with_context
async def cmd_preset(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Apply camera preset."""
    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_APPLY_PRESET",
        {"camera_id": 0, "preset": args.preset},
    )

    if ok:
        print_success(f"Applied preset: {args.preset}")
        return 0
    else:
        print_error(f"Failed to apply preset: {error}")
        return 1


@run_with_context
async def cmd_capture(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Capture a single frame."""
    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_CAPTURE_FRAME",
        {"camera_id": 0, "publish": True},
    )

    if ok:
        print_success("Frame captured")
        return 0
    else:
        print_error(f"Failed to capture: {error}")
        return 1


@run_with_context
async def cmd_start(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Start continuous capture."""
    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_START_CAPTURE",
        {"camera_id": 0, "mode": "polling", "fps": args.fps},
    )

    if ok:
        print_success(f"Started capture at {args.fps} FPS")
        return 0
    else:
        print_error(f"Failed to start capture: {error}")
        return 1


@run_with_context
async def cmd_stop(args: argparse.Namespace, ctx: CLIContext) -> int:
    """Stop continuous capture."""
    ok, error = await ctx.client.send_reliable(
        "CMD_CAM_STOP_CAPTURE",
        {"camera_id": 0},
    )

    if ok:
        print_success("Capture stopped")
        return 0
    else:
        print_error(f"Failed to stop capture: {error}")
        return 1


def cmd_list_resolutions(args: argparse.Namespace) -> int:
    """List available resolutions."""
    table = Table(title="Available Resolutions")
    table.add_column("Name", style="cyan")
    table.add_column("Dimensions", justify="right")
    table.add_column("Value", justify="center")

    for name, (value, dims) in RESOLUTIONS.items():
        table.add_row(name.upper(), dims, str(value))

    console.print(table)
    return 0
