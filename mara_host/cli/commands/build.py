# mara_host/cli/commands/build.py
"""Firmware build commands for MARA CLI."""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.panel import Panel

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
    spinner,
)

# Import build utilities from existing module
from mara_host.tools.build_firmware import (
    MCU_PROJECT,
    ENVIRONMENTS,
    FEATURES,
    PRESETS,
    parse_features,
    features_to_flags,
    build as do_build,
    upload as do_upload,
    test as do_test,
    clean as do_clean,
    generate as do_generate,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register build commands."""
    build_parser = subparsers.add_parser(
        "build",
        help="Firmware build operations",
        description="Build, upload, and test ESP32 firmware",
    )

    build_sub = build_parser.add_subparsers(
        dest="build_cmd",
        title="build commands",
        metavar="<subcommand>",
    )

    # Common arguments
    def add_common_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-e", "--env",
            default="esp32_usb",
            choices=sorted(ENVIRONMENTS),
            help="PlatformIO environment (default: esp32_usb)",
        )
        parser.add_argument(
            "-v", "--verbose",
            action="store_true",
            help="Verbose output",
        )
        parser.add_argument(
            "-g", "--generate",
            action="store_true",
            help="Run code generators first",
        )

    def add_feature_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--features",
            metavar="LIST",
            help="Comma-separated features to enable (e.g., wifi,ota,dc_motor) "
                 "or preset name (minimal, motors, sensors, control, full)",
        )
        parser.add_argument(
            "--no-features",
            metavar="LIST",
            help="Comma-separated features to disable (use with presets)",
        )
        parser.add_argument(
            "--preset",
            choices=sorted(PRESETS.keys()),
            help="Use a feature preset",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be built without building",
        )

    # compile
    compile_p = build_sub.add_parser(
        "compile",
        help="Compile firmware",
    )
    add_common_args(compile_p)
    add_feature_args(compile_p)
    compile_p.set_defaults(func=cmd_compile)

    # upload
    upload_p = build_sub.add_parser(
        "upload",
        help="Compile and flash firmware to ESP32",
    )
    add_common_args(upload_p)
    add_feature_args(upload_p)
    upload_p.set_defaults(func=cmd_upload)

    # clean
    clean_p = build_sub.add_parser(
        "clean",
        help="Clean build artifacts",
    )
    clean_p.add_argument(
        "-e", "--env",
        default=None,
        help="Environment to clean (default: all)",
    )
    clean_p.set_defaults(func=cmd_clean)

    # test
    test_p = build_sub.add_parser(
        "test",
        help="Run firmware unit tests",
    )
    test_p.add_argument(
        "--native",
        action="store_true",
        default=True,
        help="Run native tests (default)",
    )
    test_p.add_argument(
        "--device",
        action="store_true",
        help="Run tests on device",
    )
    test_p.add_argument(
        "-f", "--filter",
        dest="filter_pattern",
        help="Filter tests by pattern",
    )
    test_p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    test_p.set_defaults(func=cmd_test)

    # features
    features_p = build_sub.add_parser(
        "features",
        help="List available features and presets",
    )
    features_p.set_defaults(func=cmd_features)

    # size
    size_p = build_sub.add_parser(
        "size",
        help="Show firmware size information",
    )
    size_p.add_argument(
        "-e", "--env",
        default="esp32_usb",
        choices=sorted(ENVIRONMENTS),
        help="Environment to check (default: esp32_usb)",
    )
    size_p.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed section breakdown",
    )
    size_p.set_defaults(func=cmd_size)

    # watch
    watch_p = build_sub.add_parser(
        "watch",
        help="Watch for changes and rebuild automatically",
    )
    add_common_args(watch_p)
    add_feature_args(watch_p)
    watch_p.set_defaults(func=cmd_watch)

    # Default handler
    build_parser.set_defaults(func=lambda args: cmd_compile(args) if hasattr(args, 'env') else cmd_features(args))


def _get_features(args: argparse.Namespace) -> dict[str, bool] | None:
    """Get feature configuration from args."""
    features_str = args.features
    if args.preset:
        features_str = args.preset if not features_str else f"{args.preset},{features_str}"
    return parse_features(features_str, getattr(args, 'no_features', None))


def cmd_compile(args: argparse.Namespace) -> int:
    """Compile firmware."""
    env = getattr(args, 'env', 'esp32_usb')
    verbose = getattr(args, 'verbose', False)
    features = _get_features(args)

    if getattr(args, 'dry_run', False):
        console.print()
        console.print("[bold cyan]Dry run - would compile:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        console.print(f"  MCU Project: [dim]{MCU_PROJECT}[/dim]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        return 0

    console.print()
    console.print(f"[bold cyan]Building firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    console.print()

    # Run generators if requested
    if getattr(args, 'generate', False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    # Build with timing
    start_time = time.time()

    if verbose:
        rc = do_build(env, verbose, features)
    else:
        rc = _build_with_progress(env, features)

    elapsed = time.time() - start_time

    if rc == 0:
        print_success(f"Build completed in {elapsed:.1f}s")
        # Show size info
        _show_size_summary(env)
    else:
        print_error(f"Build failed with exit code {rc} (after {elapsed:.1f}s)")

    return rc


def _build_with_progress(env: str, features: dict[str, bool] | None) -> int:
    """Run build with progress indicator."""
    cmd = ["pio", "run", "-e", env]

    # Set up environment
    env_vars = os.environ.copy()
    if features:
        flags_str = " ".join(features_to_flags(features))
        env_vars["PLATFORMIO_BUILD_FLAGS"] = flags_str

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Compiling...", total=None)

        process = subprocess.Popen(
            cmd,
            cwd=MCU_PROJECT,
            env=env_vars,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        compiling_count = 0
        linking = False

        for line in process.stdout:
            line = line.strip()

            # Update progress based on output
            if "Compiling" in line:
                compiling_count += 1
                # Extract filename
                match = re.search(r'Compiling (.+?)\.', line)
                if match:
                    filename = match.group(1).split('/')[-1]
                    progress.update(task, description=f"Compiling {filename}... ({compiling_count})")
            elif "Linking" in line:
                progress.update(task, description="Linking...")
                linking = True
            elif "Building" in line and ".bin" in line:
                progress.update(task, description="Creating binary...")
            elif "Checking size" in line:
                progress.update(task, description="Checking size...")

        process.wait()
        return process.returncode


def cmd_upload(args: argparse.Namespace) -> int:
    """Compile and upload firmware."""
    env = getattr(args, 'env', 'esp32_usb')
    verbose = getattr(args, 'verbose', False)
    features = _get_features(args)

    if getattr(args, 'dry_run', False):
        console.print()
        console.print("[bold cyan]Dry run - would upload:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        return 0

    console.print()
    console.print(f"[bold cyan]Uploading firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    console.print()

    # Run generators if requested
    if getattr(args, 'generate', False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    rc = do_upload(env, verbose, features)

    if rc == 0:
        print_success("Upload completed successfully")
    else:
        print_error(f"Upload failed with exit code {rc}")

    return rc


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean build artifacts."""
    env = getattr(args, 'env', None)

    console.print()
    if env:
        console.print(f"[bold cyan]Cleaning build artifacts for {env}[/bold cyan]")
    else:
        console.print("[bold cyan]Cleaning all build artifacts[/bold cyan]")
    console.print()

    rc = do_clean(env)

    if rc == 0:
        print_success("Clean completed")
    else:
        print_error(f"Clean failed with exit code {rc}")

    return rc


def cmd_test(args: argparse.Namespace) -> int:
    """Run firmware unit tests."""
    native = getattr(args, 'native', True)
    device = getattr(args, 'device', False)
    filter_pattern = getattr(args, 'filter_pattern', None)
    verbose = getattr(args, 'verbose', False)

    console.print()
    console.print("[bold cyan]Running firmware tests[/bold cyan]")

    envs = []
    if native:
        envs.append("native")
    if device:
        envs.append("esp32_test")

    console.print(f"  Environments: [green]{', '.join(envs)}[/green]")
    if filter_pattern:
        console.print(f"  Filter: [yellow]{filter_pattern}[/yellow]")
    console.print()

    rc = do_test(native, device, filter_pattern, verbose)

    if rc == 0:
        print_success("All tests passed")
    else:
        print_error(f"Tests failed with exit code {rc}")

    return rc


def cmd_features(args: argparse.Namespace) -> int:
    """List available features and presets."""
    console.print()
    console.print("[bold cyan]Available Features[/bold cyan]")
    console.print()

    categories = {
        "Transport": ["wifi", "ble", "uart", "mqtt"],
        "Motors": ["servo", "stepper", "dc_motor", "encoder", "motion"],
        "Sensors": ["ultrasonic", "imu", "lidar"],
        "Control": ["signal_bus", "control_kernel", "pid", "state_space", "observer", "control_module"],
        "System": ["ota", "telemetry", "heartbeat", "logging", "identity", "audio"],
    }

    for category, feats in categories.items():
        table = Table(title=category, show_header=True, header_style="bold")
        table.add_column("Feature", style="cyan")
        table.add_column("Macro", style="dim")

        for feat in feats:
            if feat in FEATURES:
                table.add_row(feat, FEATURES[feat])

        console.print(table)
        console.print()

    console.print("[bold cyan]Presets[/bold cyan]")
    console.print()

    for preset, feats in PRESETS.items():
        console.print(f"[bold green]{preset}[/bold green]")
        console.print(f"  [dim]{', '.join(feats)}[/dim]")
        console.print()

    console.print("[dim]Usage: mara build compile --preset motors[/dim]")
    console.print("[dim]       mara build compile --features wifi,ota,dc_motor[/dim]")

    return 0


def _show_size_summary(env: str) -> None:
    """Show brief firmware size summary after build."""
    size_info = _get_firmware_size(env)
    if size_info:
        flash_pct = (size_info['flash_used'] / size_info['flash_total']) * 100
        ram_pct = (size_info['ram_used'] / size_info['ram_total']) * 100

        flash_bar = _make_bar(flash_pct, 20)
        ram_bar = _make_bar(ram_pct, 20)

        console.print()
        console.print(f"  Flash: {flash_bar} {size_info['flash_used']:,}B / {size_info['flash_total']:,}B ({flash_pct:.1f}%)")
        console.print(f"  RAM:   {ram_bar} {size_info['ram_used']:,}B / {size_info['ram_total']:,}B ({ram_pct:.1f}%)")


def _make_bar(percentage: float, width: int = 20) -> str:
    """Create a simple progress bar string."""
    filled = int(width * percentage / 100)
    empty = width - filled

    if percentage > 90:
        color = "red"
    elif percentage > 70:
        color = "yellow"
    else:
        color = "green"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


def _get_firmware_size(env: str) -> Optional[dict]:
    """Get firmware size information from PlatformIO."""
    try:
        result = subprocess.run(
            ["pio", "run", "-e", env, "-t", "size", "--silent"],
            cwd=MCU_PROJECT,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        # Parse size output
        output = result.stdout + result.stderr

        # Look for ESP32 size format
        # RAM:   [===       ]  32.5% (used 106524 bytes from 327680 bytes)
        # Flash: [====      ]  42.1% (used 552892 bytes from 1310720 bytes)

        size_info = {}

        ram_match = re.search(r'RAM:.*?(\d+\.?\d*)%.*?(\d+)\s+bytes.*?(\d+)\s+bytes', output)
        if ram_match:
            size_info['ram_used'] = int(ram_match.group(2))
            size_info['ram_total'] = int(ram_match.group(3))

        flash_match = re.search(r'Flash:.*?(\d+\.?\d*)%.*?(\d+)\s+bytes.*?(\d+)\s+bytes', output)
        if flash_match:
            size_info['flash_used'] = int(flash_match.group(2))
            size_info['flash_total'] = int(flash_match.group(3))

        if size_info:
            return size_info

        # Try alternative format (xtensa-esp32-elf-size output)
        # Look for: text    data     bss     dec     hex filename
        size_match = re.search(r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-9a-f]+)\s+', output)
        if size_match:
            text = int(size_match.group(1))
            data = int(size_match.group(2))
            bss = int(size_match.group(3))

            size_info = {
                'flash_used': text + data,
                'flash_total': 1310720,  # 1.25MB default
                'ram_used': data + bss,
                'ram_total': 327680,  # 320KB
            }
            return size_info

        return None

    except Exception:
        return None


def cmd_size(args: argparse.Namespace) -> int:
    """Show firmware size information."""
    env = args.env
    detailed = getattr(args, 'detailed', False)

    console.print()
    console.print(f"[bold cyan]Firmware Size - {env}[/bold cyan]")
    console.print()

    # Run size command
    try:
        result = subprocess.run(
            ["pio", "run", "-e", env, "-t", "size"],
            cwd=MCU_PROJECT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print_error("PlatformIO not found. Install with: pip install platformio")
        return 1

    output = result.stdout + result.stderr

    # Display the output
    if detailed:
        console.print(output)
    else:
        # Just show summary
        for line in output.split('\n'):
            if 'RAM:' in line or 'Flash:' in line:
                # Colorize the bar
                if '[' in line and ']' in line:
                    # Extract percentage
                    pct_match = re.search(r'(\d+\.?\d*)%', line)
                    if pct_match:
                        pct = float(pct_match.group(1))
                        if pct > 90:
                            console.print(f"[red]{line}[/red]")
                        elif pct > 70:
                            console.print(f"[yellow]{line}[/yellow]")
                        else:
                            console.print(f"[green]{line}[/green]")
                    else:
                        console.print(line)
                else:
                    console.print(line)

    # Show binary file info
    bin_path = MCU_PROJECT / ".pio" / "build" / env / "firmware.bin"
    if bin_path.exists():
        size_kb = bin_path.stat().st_size / 1024
        console.print()
        console.print(f"[dim]Binary: {bin_path.name} ({size_kb:.1f} KB)[/dim]")

    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch for changes and rebuild automatically."""
    env = getattr(args, 'env', 'esp32_usb')
    features = _get_features(args)

    console.print()
    console.print(f"[bold cyan]Watching for changes[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    console.print(f"  Project: [dim]{MCU_PROJECT}[/dim]")
    console.print()
    print_info("Press Ctrl+C to stop watching")
    console.print()

    try:
        # Initial build
        print_info("Running initial build...")
        rc = do_build(env, False, features)
        if rc != 0:
            print_warning("Initial build failed")

        # Watch for changes
        src_dirs = [
            MCU_PROJECT / "src",
            MCU_PROJECT / "include",
            MCU_PROJECT / "lib",
        ]

        last_mtime = _get_latest_mtime(src_dirs)

        while True:
            time.sleep(1)

            current_mtime = _get_latest_mtime(src_dirs)
            if current_mtime > last_mtime:
                console.print()
                print_info("Changes detected, rebuilding...")
                start = time.time()
                rc = do_build(env, False, features)
                elapsed = time.time() - start

                if rc == 0:
                    print_success(f"Build completed in {elapsed:.1f}s")
                    _show_size_summary(env)
                else:
                    print_error(f"Build failed")

                last_mtime = current_mtime

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching[/dim]")

    return 0


def _get_latest_mtime(dirs: list[Path]) -> float:
    """Get the latest modification time of any file in the directories."""
    latest = 0.0
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in ('.c', '.cpp', '.h', '.hpp', '.ino'):
                mtime = f.stat().st_mtime
                if mtime > latest:
                    latest = mtime
    return latest
