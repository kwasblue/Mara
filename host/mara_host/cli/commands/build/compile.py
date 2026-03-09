# cli/commands/build/compile.py
"""Compile firmware command."""

import argparse
import os
import re
import subprocess
import time

from rich.progress import Progress, SpinnerColumn, TextColumn

from mara_host.cli.console import console, print_success, print_error, print_info
from mara_host.tools.build_firmware import (
    MCU_PROJECT,
    features_to_flags,
    build as do_build,
    generate as do_generate,
)

from ._common import get_features
from .size import show_size_summary


def cmd_compile(args: argparse.Namespace) -> int:
    """Compile firmware."""
    env = getattr(args, 'env', 'esp32_usb')
    verbose = getattr(args, 'verbose', False)
    features = get_features(args)

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
        show_size_summary(env)
    else:
        print_error(f"Build failed with exit code {rc} (after {elapsed:.1f}s)")

    return rc


def _build_with_progress(env: str, features: dict[str, bool] | None) -> int:
    """Run build with progress indicator."""
    import sys
    # Use Python -m platformio for cross-platform compatibility
    cmd = [sys.executable, "-m", "platformio", "run", "-e", env]

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

        for line in process.stdout:
            line = line.strip()

            if "Compiling" in line:
                compiling_count += 1
                match = re.search(r'Compiling (.+?)\.', line)
                if match:
                    filename = match.group(1).split('/')[-1]
                    progress.update(task, description=f"Compiling {filename}... ({compiling_count})")
            elif "Linking" in line:
                progress.update(task, description="Linking...")
            elif "Building" in line and ".bin" in line:
                progress.update(task, description="Creating binary...")
            elif "Checking size" in line:
                progress.update(task, description="Checking size...")

        process.wait()
        return process.returncode
