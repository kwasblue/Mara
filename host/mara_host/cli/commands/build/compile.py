# cli/commands/build/compile.py
"""Compile firmware command."""

import argparse
import time

from rich.progress import Progress, SpinnerColumn, TextColumn

from mara_host.cli.console import console, print_success, print_error, print_info
from mara_host.services.tooling.backends import get_registry, BuildRequest
from mara_host.tools.build_firmware import (
    MCU_PROJECT,
    generate as do_generate,
)

from ._common import get_features
from .size import show_size_summary


def cmd_compile(args: argparse.Namespace) -> int:
    """Compile firmware through the pluggable BuildBackend."""
    env = getattr(args, 'env', 'esp32_usb')
    verbose = getattr(args, 'verbose', False)
    features = get_features(args)
    backend_name = getattr(args, 'build_backend', 'platformio')

    if getattr(args, 'dry_run', False):
        console.print()
        console.print("[bold cyan]Dry run - would compile:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        console.print(f"  Backend: [green]{backend_name}[/green]")
        console.print(f"  MCU Project: [dim]{MCU_PROJECT}[/dim]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        return 0

    console.print()
    console.print(f"[bold cyan]Building firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    console.print(f"  Backend: [green]{backend_name}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    console.print()

    # Run generators if requested
    if getattr(args, 'generate', False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    # Get the build backend
    registry = get_registry()
    backend = registry.get_build(backend_name)

    # Build with timing
    start_time = time.time()

    request = BuildRequest(
        environment=env,
        features=features or {},
        verbose=verbose,
        project_dir=MCU_PROJECT,
    )

    if verbose:
        # Verbose mode: backend streams output directly
        outcome = backend.build(request)
        rc = outcome.return_code
    else:
        # Non-verbose: show progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Compiling...", total=None)
            outcome = backend.build(request)
            rc = outcome.return_code

    elapsed = time.time() - start_time

    if rc == 0:
        print_success(f"Build completed in {elapsed:.1f}s")
        if outcome.firmware_size:
            console.print(f"  Firmware: [cyan]{outcome.firmware_size:,}[/cyan] bytes")
        if outcome.ram_usage:
            console.print(f"  RAM: [cyan]{outcome.ram_usage:,}[/cyan] bytes")
        show_size_summary(env, backend_name, outcome.firmware_size, outcome.ram_usage)
    else:
        print_error(f"Build failed with exit code {rc} (after {elapsed:.1f}s)")
        if outcome.error:
            console.print(f"[red]{outcome.error}[/red]")

    return rc
