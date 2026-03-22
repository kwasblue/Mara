#!/usr/bin/env python3
# mara_host/cli/main.py
"""MARA CLI - Modular Asynchronous Robotics Architecture.

AUTO-DISCOVERY: CLI commands are automatically discovered.
To add a new command, create a file in `cli/commands/` with a
`register(subparsers)` function.

Example:
    # cli/commands/mycommand.py
    def register(subparsers):
        parser = subparsers.add_parser("mycommand", help="My command")
        parser.set_defaults(func=cmd_mycommand)

    def cmd_mycommand(args):
        print("Hello from mycommand!")
        return 0

The command will be auto-discovered and registered.
"""

import argparse
import importlib
import sys
from pathlib import Path


from mara_host.cli.console import console


def _discover_commands(subparsers: argparse._SubParsersAction) -> list[str]:
    """
    Auto-discover and register CLI command modules.

    Scans cli/commands/ for modules with a register() function.
    Returns list of registered command names for debugging.
    """
    registered = []
    commands_dir = Path(__file__).parent / "commands"

    # Find all .py files and packages in commands/
    for item in sorted(commands_dir.iterdir()):
        # Skip __pycache__ and private files
        if item.name.startswith("_"):
            continue

        # Determine module name
        if item.is_file() and item.suffix == ".py":
            module_name = item.stem
        elif item.is_dir() and (item / "__init__.py").exists():
            module_name = item.name
        else:
            continue

        try:
            # Import the module
            module = importlib.import_module(
                f"mara_host.cli.commands.{module_name}"
            )

            # Check for register function
            if hasattr(module, "register") and callable(module.register):
                module.register(subparsers)
                registered.append(module_name)

        except Exception as e:
            # Log but don't fail - allows partial CLI functionality
            console.print(f"[yellow]Warning: Failed to load command '{module_name}': {e}[/yellow]")

    return registered


def _register_completions(subparsers: argparse._SubParsersAction) -> None:
    """Register shell completions command (special case - in cli/ not commands/)."""
    try:
        from mara_host.cli import completions
        if hasattr(completions, "register"):
            completions.register(subparsers)
    except ImportError:
        pass


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="mara",
        description="MARA - Modular Asynchronous Robotics Architecture CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mara pins pinout            # Show visual board diagram
  mara pins list              # List all pins with status
  mara build compile          # Build firmware
  mara generate all           # Run all code generators
  mara run serial             # Connect via serial
  mara version                # Show version info

For more help on a specific command:
  mara <command> --help
""",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress client connection messages",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="<command>",
    )

    # Auto-discover and register all commands from cli/commands/
    _discover_commands(subparsers)

    # Register completions (special location)
    _register_completions(subparsers)

    # Version command (built-in)
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information",
    )
    version_parser.set_defaults(func=cmd_version)

    # Debug command (built-in) - helps diagnose import issues
    debug_parser = subparsers.add_parser(
        "debug",
        help="Debug CLI import issues",
    )
    debug_parser.set_defaults(func=cmd_debug)

    return parser


def cmd_version(args: argparse.Namespace) -> int:
    """Show version information."""
    from mara_host import __version__

    console.print(f"[bold cyan]MARA CLI[/bold cyan] version [green]{__version__}[/green]")
    console.print("[dim]Modular Asynchronous Robotics Architecture[/dim]")
    console.print()
    console.print("[dim]Python platform for controlling robots with ESP32 MCU firmware[/dim]")
    return 0


def cmd_debug(args: argparse.Namespace) -> int:
    """Debug CLI import issues."""
    console.print("[bold cyan]MARA CLI Debug Info[/bold cyan]")
    console.print()

    # Python info
    console.print(f"[cyan]Python:[/cyan] {sys.version}")
    console.print(f"[cyan]Platform:[/cyan] {sys.platform}")
    console.print()

    # Try to import key modules
    console.print("[bold]Module Import Test:[/bold]")

    modules_to_test = [
        ("mara_host", "Core package"),
        ("mara_host.cli.console", "CLI console"),
        ("mara_host.tools.build_firmware", "Build firmware"),
        ("mara_host.cli.commands.build", "Build command"),
        ("mara_host.cli.commands.build._registry", "Build registry"),
    ]

    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            console.print(f"  [green]✓[/green] {module_name}")
        except Exception as e:
            console.print(f"  [red]✗[/red] {module_name}: {e}")

    console.print()

    # Check for platformio
    console.print("[bold]PlatformIO Check:[/bold]")
    try:
        import platformio
        console.print(f"  [green]✓[/green] platformio installed (version {platformio.__version__})")
    except ImportError:
        console.print("  [yellow]![/yellow] platformio not installed (run: pip install platformio)")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # No command specified - show help
    if not args.command:
        parser.print_help()
        return 0

    # Execute the command function
    if hasattr(args, "func"):
        try:
            return args.func(args)
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted[/dim]")
            return 130
        except Exception as e:
            if args.verbose:
                console.print_exception()
            else:
                console.print(f"[error]Error:[/error] {e}")
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
