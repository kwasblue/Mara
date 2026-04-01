# cli/commands/build/features.py
"""List features and profiles command."""

import argparse

from rich.table import Table

from mara_host.cli.console import console
from mara_host.core.build_profiles import (
    FEATURE_TO_MACRO,
    FEATURE_ALIASES,
    get_profile_names,
    get_profile,
)


def cmd_features(args: argparse.Namespace) -> int:
    """List available features and profiles."""
    console.print()
    console.print("[bold cyan]Available Features[/bold cyan]")
    console.print()

    categories = {
        "Transport": ["wifi", "ble", "uart_transport", "mqtt_transport"],
        "Motors": ["servo", "stepper", "dc_motor", "encoder", "motion_controller"],
        "Sensors": ["ultrasonic", "imu", "lidar"],
        "Control": ["signal_bus", "control_kernel", "pid_controller", "state_space", "observer", "control_module"],
        "System": ["ota", "telemetry", "heartbeat", "logging", "identity", "audio", "benchmark"],
    }

    for category, feats in categories.items():
        table = Table(title=category, show_header=True, header_style="bold")
        table.add_column("Feature", style="cyan")
        table.add_column("Macro", style="dim")
        table.add_column("Aliases", style="dim")

        for feat in feats:
            if feat in FEATURE_TO_MACRO:
                # Find aliases for this feature
                aliases = [alias for alias, canonical in FEATURE_ALIASES.items() if canonical == feat]
                alias_str = ", ".join(aliases) if aliases else ""
                table.add_row(feat, FEATURE_TO_MACRO[feat], alias_str)

        console.print(table)
        console.print()

    console.print("[bold cyan]Build Profiles[/bold cyan] [dim](from mara_build.yaml)[/dim]")
    console.print()

    for profile_name in get_profile_names():
        profile = get_profile(profile_name)
        enabled = [k for k, v in profile.items() if v]
        console.print(f"[bold green]{profile_name}[/bold green]")
        console.print(f"  [dim]{', '.join(enabled)}[/dim]")
        console.print()

    console.print("[dim]Usage: mara build compile --profile motors[/dim]")
    console.print("[dim]       mara build compile --features wifi,ota,dc_motor[/dim]")
    console.print("[dim]       mara build upload --profile full[/dim]")

    return 0
