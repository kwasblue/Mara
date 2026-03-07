# mara_host/cli/commands/pins/_registry.py
"""
Pin command registration.
"""

import argparse

from mara_host.cli.commands.pins.list import cmd_pinout, cmd_list, cmd_free
from mara_host.cli.commands.pins.info import cmd_info
from mara_host.cli.commands.pins.assign import cmd_assign, cmd_remove, cmd_clear
from mara_host.cli.commands.pins.suggest import cmd_suggest
from mara_host.cli.commands.pins.validate import cmd_validate, cmd_conflicts
from mara_host.cli.commands.pins.interactive import cmd_interactive
from mara_host.cli.commands.pins.wizard import cmd_wizard


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register pins commands."""
    pins_parser = subparsers.add_parser(
        "pins",
        help="GPIO pin management",
        description="Manage ESP32 GPIO pin assignments",
    )

    pins_sub = pins_parser.add_subparsers(
        dest="pins_cmd",
        title="pin commands",
        metavar="<subcommand>",
    )

    # pinout
    pinout_p = pins_sub.add_parser(
        "pinout",
        help="Visual board diagram with pin assignments",
    )
    pinout_p.set_defaults(func=cmd_pinout)

    # list
    list_p = pins_sub.add_parser(
        "list",
        help="Show all pins with status",
    )
    list_p.set_defaults(func=cmd_list)

    # free
    free_p = pins_sub.add_parser(
        "free",
        help="Show available pins",
    )
    free_p.set_defaults(func=cmd_free)

    # info
    info_p = pins_sub.add_parser(
        "info",
        help="Show detailed info for a specific pin",
    )
    info_p.add_argument("gpio", type=int, help="GPIO number")
    info_p.set_defaults(func=cmd_info)

    # assign
    assign_p = pins_sub.add_parser(
        "assign",
        help="Assign a name to a GPIO pin",
    )
    assign_p.add_argument("name", help="Pin name (e.g., MOTOR_PWM)")
    assign_p.add_argument("gpio", type=int, help="GPIO number")
    assign_p.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation for boot pins",
    )
    assign_p.set_defaults(func=cmd_assign)

    # remove
    remove_p = pins_sub.add_parser(
        "remove",
        help="Remove a pin assignment",
    )
    remove_p.add_argument("name", help="Pin name to remove")
    remove_p.set_defaults(func=cmd_remove)

    # suggest
    suggest_p = pins_sub.add_parser(
        "suggest",
        help="Suggest best pins for a use case",
    )
    suggest_p.add_argument(
        "use_case",
        choices=["pwm", "adc", "input", "output", "i2c", "spi", "uart", "touch", "dac"],
        help="Use case to suggest pins for",
    )
    suggest_p.set_defaults(func=cmd_suggest)

    # validate
    validate_p = pins_sub.add_parser(
        "validate",
        help="Validate current pin assignments",
    )
    validate_p.set_defaults(func=cmd_validate)

    # interactive
    interactive_p = pins_sub.add_parser(
        "interactive",
        help="Interactive pin assignment wizard",
    )
    interactive_p.set_defaults(func=cmd_interactive)

    # conflicts
    conflicts_p = pins_sub.add_parser(
        "conflicts",
        help="Check for pin conflicts and issues",
    )
    conflicts_p.set_defaults(func=cmd_conflicts)

    # wizard
    wizard_p = pins_sub.add_parser(
        "wizard",
        help="Guided setup for common pin configurations",
    )
    wizard_p.add_argument(
        "preset",
        nargs="?",
        choices=["motor", "encoder", "stepper", "i2c", "spi", "uart", "servo"],
        help="Preset to configure",
    )
    wizard_p.set_defaults(func=cmd_wizard)

    # clear
    clear_p = pins_sub.add_parser(
        "clear",
        help="Clear all pin assignments",
    )
    clear_p.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation",
    )
    clear_p.set_defaults(func=cmd_clear)

    # Default handler when no subcommand is given
    pins_parser.set_defaults(func=lambda args: cmd_list(args))
