# cli/commands/build/clean.py
"""Clean build artifacts command."""

import argparse

from mara_host.cli.console import console, print_success, print_error
from mara_host.services.tooling.backends import get_registry


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean build artifacts through the pluggable BuildBackend."""
    env = getattr(args, 'env', None)
    backend_name = getattr(args, 'build_backend', 'platformio')

    console.print()
    if env:
        console.print(f"[bold cyan]Cleaning build artifacts for {env}[/bold cyan]")
    else:
        console.print("[bold cyan]Cleaning all build artifacts[/bold cyan]")
    console.print(f"  Backend: [green]{backend_name}[/green]")
    console.print()

    registry = get_registry()
    backend = registry.get_build(backend_name)
    outcome = backend.clean(env)

    if outcome.success:
        print_success("Clean completed")
    else:
        print_error(f"Clean failed with exit code {outcome.return_code}")
        if outcome.error:
            console.print(f"[red]{outcome.error}[/red]")

    return outcome.return_code
