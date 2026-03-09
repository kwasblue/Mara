# cli/commands/build/features.py
"""List features and presets command."""

import argparse

from rich.table import Table

from mara_host.cli.console import console
from mara_host.tools.build_firmware import FEATURES, PRESETS


def cmd_features(args: argparse.Namespace) -> int:
    """List available features and presets."""
    console.print()
    console.print("[bold cyan]Available Features[/bold cyan]")
    console.print()

    categories = {
        "Transport": ["wifi", "ble", "uart", "mqtt"],
        "Motors": ["servo", "stepper", "dc_motor", "encoder", "motion"],
        "Sensors": ["ultrasonic", "imu", "lidar"],
        "Control": ["signal_bus", "control_kernel", "pid", "state_space", "observer", "control_module"],
        "System": ["ota", "telemetry", "heartbeat", "logging", "identity", "audio"],
    }

    for category, feats in categories.items():
        table = Table(title=category, show_header=True, header_style="bold")
        table.add_column("Feature", style="cyan")
        table.add_column("Macro", style="dim")

        for feat in feats:
            if feat in FEATURES:
                table.add_row(feat, FEATURES[feat])

        console.print(table)
        console.print()

    console.print("[bold cyan]Presets[/bold cyan]")
    console.print()

    for preset, feats in PRESETS.items():
        console.print(f"[bold green]{preset}[/bold green]")
        console.print(f"  [dim]{', '.join(feats)}[/dim]")
        console.print()

    console.print("[dim]Usage: mara build compile --preset motors[/dim]")
    console.print("[dim]       mara build compile --features wifi,ota,dc_motor[/dim]")

    return 0
