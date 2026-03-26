"""Upload firmware command."""

import argparse

from mara_host.cli.console import console, print_error, print_info, print_success
from mara_host.tools.build_firmware import generate as do_generate
from mara_host.tools.build_firmware import upload as do_upload

from ._common import get_features


DEFAULT_DIRECT_UPLOAD_BAUD = 115200


def cmd_upload(args: argparse.Namespace) -> int:
    """Compile and upload firmware."""
    env = getattr(args, "env", "esp32_usb")
    verbose = getattr(args, "verbose", False)
    port = getattr(args, "port", None)
    upload_baud = getattr(args, "upload_baud", None)
    direct = getattr(args, "direct", False)
    auto_retry_direct = getattr(args, "auto_retry_direct", False)
    features = get_features(args)

    if getattr(args, "dry_run", False):
        console.print()
        console.print("[bold cyan]Dry run - would upload:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        if port:
            console.print(f"  Port: [green]{port}[/green]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        if direct:
            console.print("  Mode: [yellow]direct esptool flash[/yellow]")
        elif auto_retry_direct:
            console.print(
                f"  Fallback: [yellow]retry direct flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud on upload failure[/yellow]"
            )
        if upload_baud:
            console.print(f"  Upload baud: [green]{upload_baud}[/green]")
        return 0

    console.print()
    console.print("[bold cyan]Uploading firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    if port:
        console.print(f"  Port: [green]{port}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    if direct:
        console.print("  Mode: [yellow]direct esptool flash[/yellow]")
    elif auto_retry_direct:
        console.print(
            f"  Fallback: [yellow]retry direct flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud if PlatformIO upload fails[/yellow]"
        )
    if upload_baud:
        console.print(f"  Upload baud: [green]{upload_baud}[/green]")

    console.print()

    if getattr(args, "generate", False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    rc = do_upload(
        env,
        verbose,
        features,
        port=port,
        upload_baud=upload_baud,
        direct=direct,
    )

    if rc != 0 and auto_retry_direct and not direct and upload_baud is None:
        if not port:
            print_error("PlatformIO upload failed and direct retry requires --port")
            return rc

        print_info(
            f"PlatformIO upload failed; retrying with direct esptool flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud..."
        )
        rc = do_upload(
            env,
            verbose,
            features,
            port=port,
            upload_baud=DEFAULT_DIRECT_UPLOAD_BAUD,
            direct=True,
        )

    if rc == 0:
        print_success("Upload completed successfully")
    else:
        print_error(f"Upload failed with exit code {rc}")

    return rc
