# mara_host/cli/commands/generate.py
"""Code generation commands for MARA CLI."""

import argparse
import sys
from pathlib import Path

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)

# Path to tools directory
TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register generate commands."""
    gen_parser = subparsers.add_parser(
        "generate",
        help="Code generation",
        description="Run code generators for Host and MCU projects",
    )

    gen_sub = gen_parser.add_subparsers(
        dest="gen_cmd",
        title="generators",
        metavar="<generator>",
    )

    # all
    all_p = gen_sub.add_parser(
        "all",
        help="Run all code generators",
    )
    all_p.set_defaults(func=cmd_all)

    # commands
    cmd_p = gen_sub.add_parser(
        "commands",
        help="Generate command definitions",
    )
    cmd_p.set_defaults(func=cmd_commands)

    # pins
    pins_p = gen_sub.add_parser(
        "pins",
        help="Generate pin configuration",
    )
    pins_p.set_defaults(func=cmd_pins)

    # can
    can_p = gen_sub.add_parser(
        "can",
        help="Generate CAN bus definitions",
    )
    can_p.set_defaults(func=cmd_can)

    # telemetry
    telem_p = gen_sub.add_parser(
        "telemetry",
        help="Generate telemetry sections",
    )
    telem_p.set_defaults(func=cmd_telemetry)

    # binary
    binary_p = gen_sub.add_parser(
        "binary",
        help="Generate binary command definitions",
    )
    binary_p.set_defaults(func=cmd_binary)

    # gpio
    gpio_p = gen_sub.add_parser(
        "gpio",
        help="Generate GPIO channel mappings",
    )
    gpio_p.set_defaults(func=cmd_gpio)

    # Default handler
    gen_parser.set_defaults(func=cmd_all)


def _run_generator(name: str, module_name: str) -> int:
    """Run a single generator module."""
    console.print(f"  [cyan]{name}[/cyan]...", end=" ")

    try:
        # Ensure tools dir is in path
        if str(TOOLS_DIR) not in sys.path:
            sys.path.insert(0, str(TOOLS_DIR))

        # Import and run the generator
        module = __import__(module_name)
        module.main()
        console.print("[green]done[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]failed[/red]")
        console.print(f"    [red]{e}[/red]")
        return 1


def cmd_all(args: argparse.Namespace) -> int:
    """Run all code generators."""
    console.print()
    console.print("[bold cyan]Running all code generators[/bold cyan]")
    console.print()

    generators = [
        ("Command definitions", "gen_commands"),
        ("Pin configuration", "generate_pins"),
        ("GPIO channel mappings", "gpio_mapping_gen"),
        ("Binary commands", "gen_binary_commands"),
        ("Telemetry sections", "gen_telemetry"),
        ("CAN bus definitions", "gen_can"),
    ]

    errors = 0
    for name, module in generators:
        rc = _run_generator(name, module)
        if rc != 0:
            errors += 1

    console.print()
    if errors == 0:
        print_success("All generators completed successfully")
    else:
        print_error(f"{errors} generator(s) failed")

    return 1 if errors > 0 else 0


def cmd_commands(args: argparse.Namespace) -> int:
    """Generate command definitions."""
    console.print()
    console.print("[bold cyan]Generating command definitions[/bold cyan]")
    console.print()

    rc = _run_generator("Commands", "gen_commands")

    console.print()
    if rc == 0:
        print_success("Command definitions generated")
        print_info("Generated: CommandDefs.h, command_defs.py, client_commands.py, commands.json")
    return rc


def cmd_pins(args: argparse.Namespace) -> int:
    """Generate pin configuration."""
    console.print()
    console.print("[bold cyan]Generating pin configuration[/bold cyan]")
    console.print()

    rc = _run_generator("Pins", "generate_pins")

    console.print()
    if rc == 0:
        print_success("Pin configuration generated")
        print_info("Generated: PinConfig.h, pin_config.py")
    return rc


def cmd_can(args: argparse.Namespace) -> int:
    """Generate CAN bus definitions."""
    console.print()
    console.print("[bold cyan]Generating CAN bus definitions[/bold cyan]")
    console.print()

    rc = _run_generator("CAN", "gen_can")

    console.print()
    if rc == 0:
        print_success("CAN bus definitions generated")
        print_info("Generated: CanDefs.h, can_defs_generated.py")
    return rc


def cmd_telemetry(args: argparse.Namespace) -> int:
    """Generate telemetry sections."""
    console.print()
    console.print("[bold cyan]Generating telemetry sections[/bold cyan]")
    console.print()

    rc = _run_generator("Telemetry", "gen_telemetry")

    console.print()
    if rc == 0:
        print_success("Telemetry sections generated")
    return rc


def cmd_binary(args: argparse.Namespace) -> int:
    """Generate binary command definitions."""
    console.print()
    console.print("[bold cyan]Generating binary command definitions[/bold cyan]")
    console.print()

    rc = _run_generator("Binary commands", "gen_binary_commands")

    console.print()
    if rc == 0:
        print_success("Binary command definitions generated")
        print_info("Generated: BinaryCommands.h, binary_commands.py, json_to_binary.py")
    return rc


def cmd_gpio(args: argparse.Namespace) -> int:
    """Generate GPIO channel mappings."""
    console.print()
    console.print("[bold cyan]Generating GPIO channel mappings[/bold cyan]")
    console.print()

    rc = _run_generator("GPIO channels", "gpio_mapping_gen")

    console.print()
    if rc == 0:
        print_success("GPIO channel mappings generated")
        print_info("Generated: GpioChannelDefs.h, gpio_channels.py")
    return rc
