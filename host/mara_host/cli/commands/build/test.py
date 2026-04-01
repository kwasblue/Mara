# cli/commands/build/test.py
"""Run firmware tests command — uses FirmwareTestService."""

import argparse

from mara_host.cli.console import console, print_success, print_error
from mara_host.services import FirmwareTestService


def cmd_test(args: argparse.Namespace) -> int:
    """Run firmware unit tests through FirmwareTestService."""
    native = getattr(args, "native", True)
    device = getattr(args, "device", False)
    filter_pattern = getattr(args, "filter_pattern", None)
    verbose = getattr(args, "verbose", False)
    backend_name = getattr(args, "test_backend", "platformio")

    # Build the list of environments
    envs: list[str] = []
    if native:
        envs.append("native")
    if device:
        envs.append("device")
    if not envs:
        envs.append("native")

    console.print()
    console.print("[bold cyan]Running firmware tests[/bold cyan]")
    console.print(f"  Backend:      [green]{backend_name}[/green]")
    console.print(f"  Environments: [green]{', '.join(envs)}[/green]")
    if filter_pattern:
        console.print(f"  Filter:       [yellow]{filter_pattern}[/yellow]")
    console.print()

    # Use service
    service = FirmwareTestService(backend_name=backend_name)
    result = service.run_tests(
        environments=envs,
        filter_pattern=filter_pattern,
        verbose=verbose,
    )

    if result.success:
        print_success("All tests passed")
        return 0
    else:
        print_error(result.message)
        # Get return code from result data if available
        test_result = result.data.get("result") if result.data else None
        return test_result.return_code if test_result else 1
