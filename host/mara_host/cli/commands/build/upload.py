# cli/commands/build/upload.py
"""Upload firmware command."""

import argparse

from mara_host.cli.console import console, print_success, print_error, print_info
from mara_host.tools.build_firmware import (
    upload as do_upload,
    generate as do_generate,
)

from ._common import get_features


def cmd_upload(args: argparse.Namespace) -> int:
    """Compile and upload firmware."""
    env = getattr(args, 'env', 'esp32_usb')
    verbose = getattr(args, 'verbose', False)
    port = getattr(args, 'port', None)
    features = get_features(args)

    if getattr(args, 'dry_run', False):
        console.print()
        console.print("[bold cyan]Dry run - would upload:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        if port:
            console.print(f"  Port: [green]{port}[/green]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        return 0

    console.print()
    console.print(f"[bold cyan]Uploading firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    if port:
        console.print(f"  Port: [green]{port}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    console.print()

    if getattr(args, 'generate', False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    rc = do_upload(env, verbose, features, port=port)

    if rc == 0:
        print_success("Upload completed successfully")
    else:
        print_error(f"Upload failed with exit code {rc}")

    return rc
