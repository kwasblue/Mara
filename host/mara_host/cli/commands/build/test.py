# cli/commands/build/test.py
"""Run firmware tests command."""

import argparse

from mara_host.cli.console import console, print_success, print_error
from mara_host.tools.build_firmware import test as do_test


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
