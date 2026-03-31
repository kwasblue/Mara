# cli/commands/build/test.py
"""Run firmware tests command — delegates to the TestBackend interface."""

import argparse

from mara_host.cli.console import console, print_success, print_error
from mara_host.services.build.backends import get_registry, TestRequest
from mara_host.services.build.backends.models import TestEnvironment


def cmd_test(args: argparse.Namespace) -> int:
    """Run firmware unit tests through the pluggable TestBackend."""
    native = getattr(args, "native", True)
    device = getattr(args, "device", False)
    filter_pattern = getattr(args, "filter_pattern", None)
    verbose = getattr(args, "verbose", False)
    backend_name = getattr(args, "test_backend", "platformio")

    # Build the list of MARA-level test environments
    envs: list[TestEnvironment] = []
    if native:
        envs.append(TestEnvironment.NATIVE)
    if device:
        envs.append(TestEnvironment.DEVICE)
    if not envs:
        envs.append(TestEnvironment.NATIVE)

    console.print()
    console.print("[bold cyan]Running firmware tests[/bold cyan]")
    console.print(f"  Backend:      [green]{backend_name}[/green]")
    console.print(f"  Environments: [green]{', '.join(str(e) for e in envs)}[/green]")
    if filter_pattern:
        console.print(f"  Filter:       [yellow]{filter_pattern}[/yellow]")
    console.print()

    # Resolve backend from the registry
    registry = get_registry()
    try:
        backend = registry.get_test(backend_name)
    except KeyError:
        available = registry.list_test_backends()
        print_error(
            f"Unknown test backend '{backend_name}'. "
            f"Available: {', '.join(available) or '(none registered)'}"
        )
        return 1

    # Build a MARA-owned request and delegate
    request = TestRequest(
        environments=envs,
        filter_pattern=filter_pattern,
        verbose=verbose,
    )
    outcome = backend.run_tests(request)

    if outcome.success:
        print_success("All tests passed")
    else:
        print_error(f"Tests failed with exit code {outcome.return_code}")

    return outcome.return_code
