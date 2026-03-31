# mara_host/cli/commands/test/hil.py
"""HIL (Hardware-in-the-Loop) pytest test runner."""

import subprocess
import sys
from pathlib import Path
from argparse import Namespace

from mara_host.cli.console import console, print_info, print_success, print_error


def cmd_hil(args: Namespace) -> int:
    """Run HIL pytest tests."""
    # Find the tests directory
    tests_dir = Path(__file__).parent.parent.parent.parent.parent / "tests"

    if not tests_dir.exists():
        print_error(f"Tests directory not found: {tests_dir}")
        return 1

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", str(tests_dir), "-v", "--run-hil"]

    # Add transport options
    if args.port:
        cmd.extend(["--mcu-port", args.port])
    if args.tcp:
        cmd.extend(["--robot-host", args.tcp])

    # Add test filter
    if args.filter:
        cmd.extend(["-k", args.filter])

    # Add specific test file
    if args.test:
        test_file = tests_dir / args.test
        if not test_file.exists() and not args.test.startswith("test_"):
            test_file = tests_dir / f"test_{args.test}.py"
        if not test_file.exists():
            test_file = tests_dir / f"test_hil_{args.test}.py"
        if test_file.exists():
            cmd[3] = str(test_file)  # Replace tests_dir with specific file
        else:
            print_error(f"Test file not found: {args.test}")
            return 1

    # Add extra pytest args
    if args.extra:
        cmd.extend(args.extra.split())

    # Show what we're running
    console.print()
    print_info(f"Running: {' '.join(cmd)}")
    console.print()

    # Run pytest
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print_success("HIL tests passed")
    else:
        print_error(f"HIL tests failed (exit code {result.returncode})")

    return result.returncode


def cmd_hil_smoke(args: Namespace) -> int:
    """Run quick smoke tests."""
    args.test = "hil_smoke"
    return cmd_hil(args)


def cmd_hil_churn(args: Namespace) -> int:
    """Run stress/churn tests."""
    args.test = "hil_churn"
    args.extra = f"--churn-cycles={args.cycles}" + (f" {args.extra}" if args.extra else "")
    return cmd_hil(args)
