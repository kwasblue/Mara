# cli/commands/build/watch.py
"""Watch and rebuild command."""

import argparse
import time
from pathlib import Path

from mara_host.cli.console import console, print_success, print_error, print_warning, print_info
from mara_host.tools.build_firmware import (
    MCU_PROJECT,
    build as do_build,
)

from ._common import get_features
from .size import show_size_summary


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch for changes and rebuild automatically."""
    env = getattr(args, 'env', 'esp32_usb')
    features = get_features(args)

    console.print()
    console.print(f"[bold cyan]Watching for changes[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    console.print(f"  Project: [dim]{MCU_PROJECT}[/dim]")
    console.print()
    print_info("Press Ctrl+C to stop watching")
    console.print()

    try:
        print_info("Running initial build...")
        rc = do_build(env, False, features)
        if rc != 0:
            print_warning("Initial build failed")

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
                    show_size_summary(env)
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
