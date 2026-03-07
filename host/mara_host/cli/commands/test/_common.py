# mara_host/cli/commands/test/_common.py
"""Common utilities for test commands."""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
)

if TYPE_CHECKING:
    from mara_host.command.client import MaraClient


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    duration_ms: float = 0
    status: str = "pass"  # "pass", "fail", "expected", "skipped"


def print_results(results: list[TestResult], show_expected: bool = True) -> None:
    """Print test results table."""
    console.print()

    table = Table(title="Test Results", show_header=True)
    table.add_column("Test", style="cyan")
    table.add_column("Result", justify="center")
    table.add_column("Time", justify="right")
    table.add_column("Message")

    for r in results:
        # Determine display based on status
        if r.status == "pass":
            result_str = "[green]PASS[/green]"
            msg = r.message
        elif r.status == "expected":
            result_str = "[yellow]EXPCT[/yellow]"
            msg = f"[dim]{r.message}[/dim]"
        elif r.status == "skipped":
            result_str = "[dim]SKIP[/dim]"
            msg = f"[dim]{r.message}[/dim]"
        else:  # fail
            result_str = "[red]FAIL[/red]"
            msg = f"[red]{r.message}[/red]"

        time_str = f"{r.duration_ms:.0f}ms" if r.duration_ms > 0 else "-"
        table.add_row(r.name, result_str, time_str, msg)

    console.print(table)

    passed = sum(1 for r in results if r.status == "pass")
    expected = sum(1 for r in results if r.status == "expected")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "fail")

    console.print()
    if failed == 0:
        if expected > 0 or skipped > 0:
            print_success(f"{passed} passed, {expected} expected failures, {skipped} skipped")
        else:
            print_success(f"All {passed} tests passed")
    else:
        print_error(f"{failed} failed, {passed} passed, {expected} expected, {skipped} skipped")


def create_client_from_args(args) -> "MaraClient":
    """Create client from args (uses factory if available, falls back to direct)."""
    from mara_host.command.factory import create_client_from_args as factory_create
    return factory_create(args)
