"""Upload firmware command."""

import argparse

from mara_host.cli.console import console, print_error, print_info, print_success
from mara_host.services.tooling.backends import get_registry, BuildRequest, FlashRequest
from mara_host.tools.build_firmware import MCU_PROJECT, generate as do_generate
from mara_host.core._generated_config import DEFAULT_UPLOAD_BAUD_RATE

from ._common import get_features


# Use upload baud rate from generated config (single source of truth)
DEFAULT_DIRECT_UPLOAD_BAUD = DEFAULT_UPLOAD_BAUD_RATE


def cmd_upload(args: argparse.Namespace) -> int:
    """Compile and upload firmware through the pluggable backends."""
    env = getattr(args, "env", "esp32_usb")
    verbose = getattr(args, "verbose", False)
    port = getattr(args, "port", None)
    upload_baud = getattr(args, "upload_baud", None)
    direct = getattr(args, "direct", False)
    auto_retry_direct = getattr(args, "auto_retry_direct", False)
    features = get_features(args)
    backend_name = getattr(args, "build_backend", "platformio")

    if getattr(args, "dry_run", False):
        console.print()
        console.print("[bold cyan]Dry run - would upload:[/bold cyan]")
        console.print(f"  Environment: [green]{env}[/green]")
        console.print(f"  Backend: [green]{backend_name}[/green]")
        if port:
            console.print(f"  Port: [green]{port}[/green]")
        if features:
            enabled = [k for k, v in features.items() if v]
            console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")
        if direct:
            console.print("  Mode: [yellow]direct flash[/yellow]")
        elif auto_retry_direct:
            console.print(
                f"  Fallback: [yellow]retry direct flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud on failure[/yellow]"
            )
        if upload_baud:
            console.print(f"  Upload baud: [green]{upload_baud}[/green]")
        return 0

    console.print()
    console.print("[bold cyan]Uploading firmware[/bold cyan]")
    console.print(f"  Environment: [green]{env}[/green]")
    console.print(f"  Backend: [green]{backend_name}[/green]")
    if port:
        console.print(f"  Port: [green]{port}[/green]")

    if features:
        enabled = [k for k, v in features.items() if v]
        console.print(f"  Features: [yellow]{', '.join(enabled)}[/yellow]")

    if direct:
        console.print("  Mode: [yellow]direct flash[/yellow]")
    elif auto_retry_direct:
        console.print(
            f"  Fallback: [yellow]retry direct flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud on failure[/yellow]"
        )
    if upload_baud:
        console.print(f"  Upload baud: [green]{upload_baud}[/green]")

    console.print()

    if getattr(args, "generate", False):
        print_info("Running code generators...")
        do_generate()
        console.print()

    # Get backends
    registry = get_registry()
    build_backend = registry.get_build(backend_name)
    flash_backend = registry.get_flash(backend_name)

    # For direct flash mode, we need to build first
    if direct or upload_baud:
        print_info("Building firmware...")
        build_request = BuildRequest(
            environment=env,
            features=features or {},
            verbose=verbose,
            project_dir=MCU_PROJECT,
        )
        build_outcome = build_backend.build(build_request)
        if not build_outcome.success:
            print_error(f"Build failed with exit code {build_outcome.return_code}")
            if build_outcome.error:
                console.print(f"[red]{build_outcome.error}[/red]")
            return build_outcome.return_code

    # Flash the firmware
    flash_request = FlashRequest(
        environment=env,
        port=port,
        baud=upload_baud or DEFAULT_DIRECT_UPLOAD_BAUD,
        verbose=verbose,
        project_dir=MCU_PROJECT,
        direct=direct or (upload_baud is not None),
    )
    outcome = flash_backend.flash(flash_request)
    rc = outcome.return_code

    # Auto-retry with direct flash if initial upload failed
    if rc != 0 and auto_retry_direct and not direct and upload_baud is None:
        if not port:
            print_error("Upload failed and direct retry requires --port")
            return rc

        print_info(
            f"Upload failed; retrying with direct flash at {DEFAULT_DIRECT_UPLOAD_BAUD} baud..."
        )
        # Build first for direct mode
        build_request = BuildRequest(
            environment=env,
            features=features or {},
            verbose=verbose,
            project_dir=MCU_PROJECT,
        )
        build_outcome = build_backend.build(build_request)
        if not build_outcome.success:
            print_error(f"Build failed with exit code {build_outcome.return_code}")
            return build_outcome.return_code

        # Retry flash with direct mode
        flash_request = FlashRequest(
            environment=env,
            port=port,
            baud=DEFAULT_DIRECT_UPLOAD_BAUD,
            verbose=verbose,
            project_dir=MCU_PROJECT,
            direct=True,
        )
        outcome = flash_backend.flash(flash_request)
        rc = outcome.return_code

    if rc == 0:
        print_success("Upload completed successfully")
    else:
        print_error(f"Upload failed with exit code {rc}")
        if outcome.error:
            console.print(f"[red]{outcome.error}[/red]")

    return rc
