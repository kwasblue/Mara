# mara_host/cli/commands/pins.py
"""
Pin management commands for MARA CLI.

This module provides the CLI interface for pin management.
Business logic is delegated to PinService.
"""

import argparse
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_pinout_panel,
    confirm,
    create_pin_table,
    format_pin_status,
)

# Import only path constant from tools (for file save message)
from mara_host.tools.pins import PINS_JSON

# Import business logic from service layer
from mara_host.services.pins import (
    PinService,
    PinConflict,
    PinRecommendation,
    GroupRecommendation,
)


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

    # wizard (guided setup for common configurations)
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


def cmd_pinout(args: argparse.Namespace) -> int:
    """Display visual ASCII pinout diagram."""
    service = PinService()
    pinout_text = service.generate_pinout_diagram()

    # Print with rich formatting
    console.print()
    print_pinout_panel(pinout_text, "ESP32 DevKit V1 - Pin Assignment")

    # Save to file
    pinout_file = PINS_JSON.parent / "pinout.txt"
    pinout_file.write_text(pinout_text)
    print_info(f"Saved to: {pinout_file}")

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all pins with their status."""
    service = PinService()
    assignments = service.get_assignments_by_gpio()
    all_pins = service.get_all_pins()
    all_gpios = sorted(all_pins.keys())

    console.print()
    console.print("[bold cyan]ESP32 GPIO Pin Status[/bold cyan]")
    console.print()

    table = create_pin_table()

    for gpio in all_gpios:
        info = service.get_pin_info(gpio)
        if not info:
            continue

        # Status with styling
        status_text, status_style = format_pin_status(
            gpio=gpio,
            assigned_name=assignments.get(gpio),
            is_flash=service.is_flash_pin(gpio),
            is_boot=service.is_boot_pin(gpio),
            is_input_only=service.is_input_only(gpio),
            has_warning=bool(info.warning),
        )

        # Capabilities
        caps = service.capability_string(gpio)

        # Notes (truncated)
        notes = info.notes[:40] + "..." if len(info.notes) > 43 else info.notes

        table.add_row(
            str(gpio),
            f"[{status_style}]{status_text}[/{status_style}]",
            caps,
            notes,
        )

    console.print(table)

    # Summary
    pins = service.get_assignments()
    used = len(pins)
    flash_pins = service.get_flash_pins()
    usable = len([g for g in all_pins if g not in flash_pins])
    safe_set = service.get_safe_pin_set()
    safe_used = len([g for g in pins.values() if g in safe_set])
    console.print()
    console.print(f"[dim]Assigned: {used}/{usable} usable pins[/dim]")
    console.print(f"[dim]Safe pins available: {len(service.get_safe_pins()) - safe_used}[/dim]")

    return 0


def cmd_free(args: argparse.Namespace) -> int:
    """Show only available pins."""
    service = PinService()
    free_by_category = service.get_free_pins_by_category()

    console.print()
    console.print("[bold cyan]Available GPIO Pins[/bold cyan]")
    console.print()

    def print_pin_section(title: str, gpios: list[int], style: str = "white") -> None:
        """Print a section of pins."""
        if not gpios:
            return

        console.print(f"[bold {style}]{title}[/bold {style}]")
        table = create_pin_table()

        for gpio in gpios:
            info = service.get_pin_info(gpio)
            if not info:
                continue
            status_text, status_style = format_pin_status(
                gpio=gpio,
                assigned_name=None,
                is_flash=service.is_flash_pin(gpio),
                is_boot=service.is_boot_pin(gpio),
                is_input_only=service.is_input_only(gpio),
                has_warning=bool(info.warning),
            )
            table.add_row(
                str(gpio),
                f"[{status_style}]{status_text}[/{status_style}]",
                service.capability_string(gpio),
                info.notes[:40],
            )

        console.print(table)
        console.print()

    # Recommended (safe) pins first
    print_pin_section("RECOMMENDED (no boot/flash restrictions)", free_by_category["safe"], "green")

    # Input-only pins
    print_pin_section("INPUT-ONLY PINS (GPIO 34-39, no output/PWM)", free_by_category["input_only"], "blue")

    # Boot pins (usable with caution)
    print_pin_section("BOOT PINS (usable but check warnings)", free_by_category["boot"], "yellow")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed info for a specific pin."""
    service = PinService()
    gpio = args.gpio

    info = service.get_pin_info(gpio)
    if not info:
        print_error(f"GPIO {gpio} not found in ESP32 pinout")
        return 1

    assignments = service.get_assignments_by_gpio()

    console.print()
    console.print(f"[bold cyan]GPIO {gpio}[/bold cyan]")
    console.print()

    # Status
    if gpio in assignments:
        console.print(f"[bold]Status:[/bold]       [green]ASSIGNED as '{assignments[gpio]}'[/green]")
    elif service.is_flash_pin(gpio):
        console.print(f"[bold]Status:[/bold]       [red]UNUSABLE (connected to flash)[/red]")
    else:
        console.print(f"[bold]Status:[/bold]       [cyan]Available[/cyan]")

    console.print(f"[bold]Capabilities:[/bold] {service.capability_string(gpio)}")
    console.print(f"[bold]Notes:[/bold]        {info.notes}")

    if info.adc_channel:
        console.print(f"[bold]ADC:[/bold]          {info.adc_channel}")
    if info.touch_channel is not None:
        console.print(f"[bold]Touch:[/bold]        Touch{info.touch_channel}")
    if info.rtc_gpio is not None:
        console.print(f"[bold]RTC GPIO:[/bold]     {info.rtc_gpio}")

    if info.warning:
        console.print()
        print_warning(info.warning)

    if service.is_safe_pin(gpio):
        console.print()
        print_success("This is a safe, recommended pin for general use.")

    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    """Assign a name to a GPIO pin."""
    service = PinService()
    name = args.name.upper()
    gpio = args.gpio

    # Check for warning and prompt if needed
    info = service.get_pin_info(gpio)
    if info and info.warning and not args.force:
        print_warning(info.warning)
        if not confirm("Continue anyway?"):
            console.print("[dim]Cancelled.[/dim]")
            return 0

    # Delegate to service
    success, message = service.assign(name, gpio)

    if success:
        print_success(message)
        console.print()
        print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")
        return 0
    else:
        print_error(message)
        return 1


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a pin assignment."""
    service = PinService()
    name = args.name.upper()

    success, message = service.remove(name)

    if success:
        print_success(message)
        console.print()
        print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")
        return 0
    else:
        print_error(message)
        return 1


def cmd_suggest(args: argparse.Namespace) -> int:
    """Suggest best pins for a specific use case."""
    service = PinService()
    use_case = args.use_case

    console.print()
    console.print(f"[bold cyan]Best pins for {use_case.upper()}[/bold cyan]")
    console.print()

    # Get recommendations from service
    recommendations = service.suggest_pins(use_case, count=10)

    if not recommendations:
        print_warning("No available pins match this use case.")
        return 0

    table = create_pin_table()
    for rec in recommendations:
        info = service.get_pin_info(rec.gpio)
        if not info:
            continue

        status_text, status_style = format_pin_status(
            gpio=rec.gpio,
            assigned_name=None,
            is_flash=service.is_flash_pin(rec.gpio),
            is_boot=service.is_boot_pin(rec.gpio),
            is_input_only=service.is_input_only(rec.gpio),
            has_warning=bool(rec.warnings),
        )
        table.add_row(
            str(rec.gpio),
            f"[{status_style}]{status_text}[/{status_style}]",
            service.capability_string(rec.gpio),
            info.notes[:40],
        )

    console.print(table)

    # Show use case notes from service
    notes = service.get_use_case_notes(use_case)
    if notes:
        console.print()
        for note in notes:
            print_info(note)

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate current pin assignments for issues."""
    service = PinService()
    pins = service.get_assignments()

    # Use service for conflict detection
    conflicts = service.detect_conflicts()

    errors = [c for c in conflicts if c.severity == "error"]
    warnings = [c for c in conflicts if c.severity == "warning"]

    console.print()
    console.print("[bold cyan]Pin Assignment Validation[/bold cyan]")
    console.print()

    if errors:
        console.print("[bold red]ERRORS:[/bold red]")
        for c in errors:
            console.print(f"  [red]\u2717[/red] {c.message}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for c in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  {c.message}")
        console.print()

    if not errors and not warnings:
        print_success("All pin assignments look good!")
        console.print()

    console.print(f"[dim]Total: {len(pins)} pins assigned[/dim]")

    return 1 if errors else 0


def cmd_conflicts(args: argparse.Namespace) -> int:
    """Check for pin conflicts and potential issues."""
    service = PinService()
    pins = service.get_assignments()

    # Use service for conflict detection
    conflicts = service.detect_conflicts()

    console.print()
    console.print("[bold cyan]Pin Conflict Analysis[/bold cyan]")
    console.print()

    errors = [c for c in conflicts if c.severity == "error"]
    warnings = [c for c in conflicts if c.severity == "warning"]

    if errors:
        console.print("[bold red]CONFLICTS:[/bold red]")
        for c in errors:
            console.print(f"  [red]\u2717[/red] [bold]{c.conflict_type}:[/bold] {c.message}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for c in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  [bold]{c.conflict_type}:[/bold] {c.message}")
        console.print()

    # Show boot pins in use separately for clarity
    boot_conflicts = [c for c in conflicts if c.conflict_type == "boot_pin"]
    if boot_conflicts:
        console.print("[bold yellow]BOOT PINS IN USE:[/bold yellow]")
        for c in boot_conflicts:
            console.print(f"  [yellow]\u26a0[/yellow]  GPIO {c.gpio}")
            console.print(f"      [dim]{c.message}[/dim]")
        console.print()

    if not conflicts:
        print_success("No conflicts or issues detected!")
        console.print()

    # Summary
    console.print(f"[dim]Analyzed {len(pins)} pin assignments[/dim]")

    return 1 if errors else 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Interactive pin assignment mode."""
    console.print()
    console.print("[bold cyan]Interactive Pin Assignment[/bold cyan]")
    console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]")
    console.print()

    while True:
        try:
            cmd = Prompt.ask("[green]pins>[/green]").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting...[/dim]")
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0]

        if action in ("quit", "exit", "q"):
            break
        elif action == "help":
            _interactive_help()
        elif action == "list":
            cmd_list(args)
        elif action == "free":
            cmd_free(args)
        elif action == "pinout":
            cmd_pinout(args)
        elif action == "info" and len(parts) > 1:
            try:
                gpio = int(parts[1])
                args.gpio = gpio
                cmd_info(args)
            except ValueError:
                print_error(f"Invalid GPIO number: {parts[1]}")
        elif action == "assign" and len(parts) >= 3:
            name = parts[1].upper()
            try:
                gpio = int(parts[2])
                _do_assign(name, gpio, force=False)
            except ValueError:
                print_error(f"Invalid GPIO number: {parts[2]}")
        elif action == "remove" and len(parts) > 1:
            name = parts[1].upper()
            _do_remove(name)
        elif action == "suggest" and len(parts) > 1:
            use_case = parts[1]
            if use_case in ["pwm", "adc", "input", "output", "i2c", "spi", "uart", "touch", "dac"]:
                args.use_case = use_case
                cmd_suggest(args)
            else:
                print_error(f"Unknown use case: {use_case}")
        elif action == "conflicts":
            cmd_conflicts(args)
        elif action == "validate":
            cmd_validate(args)
        elif action == "save":
            print_success("Pins are automatically saved after each change")
        else:
            print_error(f"Unknown command: {action}")
            console.print("[dim]Type 'help' for available commands[/dim]")

    return 0


def _interactive_help() -> None:
    """Show interactive mode help."""
    console.print()
    console.print("[bold]Available Commands:[/bold]")
    console.print()
    console.print("  [cyan]list[/cyan]                  Show all pins")
    console.print("  [cyan]free[/cyan]                  Show available pins")
    console.print("  [cyan]pinout[/cyan]                Show board diagram")
    console.print("  [cyan]info <gpio>[/cyan]           Show details for a pin")
    console.print("  [cyan]assign <name> <gpio>[/cyan]  Assign a pin")
    console.print("  [cyan]remove <name>[/cyan]         Remove assignment")
    console.print("  [cyan]suggest <use_case>[/cyan]    Suggest pins (pwm, adc, i2c, etc.)")
    console.print("  [cyan]conflicts[/cyan]             Check for conflicts")
    console.print("  [cyan]validate[/cyan]              Validate assignments")
    console.print("  [cyan]quit[/cyan]                  Exit interactive mode")
    console.print()


def _do_assign(name: str, gpio: int, force: bool = False) -> bool:
    """Assign a pin (helper for interactive mode)."""
    service = PinService()

    info = service.get_pin_info(gpio)
    if info and info.warning and not force:
        print_warning(info.warning)
        if not Confirm.ask("Continue anyway?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return False

    success, message = service.assign(name, gpio)
    if success:
        print_success(message)
        return True
    else:
        print_error(message)
        return False


def _do_remove(name: str) -> bool:
    """Remove a pin assignment (helper for interactive mode)."""
    service = PinService()

    success, message = service.remove(name)
    if success:
        print_success(message)
        return True
    else:
        print_error(message)
        return False


def cmd_wizard(args: argparse.Namespace) -> int:
    """Guided setup wizard for common pin configurations."""
    preset = getattr(args, 'preset', None)

    console.print()
    console.print("[bold cyan]Pin Configuration Wizard[/bold cyan]")
    console.print()

    if not preset:
        # Show available presets
        console.print("Available configurations:")
        console.print()
        console.print("  [cyan]motor[/cyan]     DC motor with direction control (PWM + IN1 + IN2)")
        console.print("  [cyan]encoder[/cyan]   Quadrature encoder (A + B channels)")
        console.print("  [cyan]stepper[/cyan]   Stepper motor (STEP + DIR + EN)")
        console.print("  [cyan]servo[/cyan]     Servo motor (single PWM pin)")
        console.print("  [cyan]i2c[/cyan]       I2C bus (SDA + SCL)")
        console.print("  [cyan]spi[/cyan]       SPI bus (MOSI + MISO + CLK + CS)")
        console.print("  [cyan]uart[/cyan]      UART (TX + RX)")
        console.print()
        preset = Prompt.ask(
            "Select configuration",
            choices=["motor", "encoder", "stepper", "servo", "i2c", "spi", "uart"],
        )

    if preset == "motor":
        return _wizard_motor()
    elif preset == "encoder":
        return _wizard_encoder()
    elif preset == "stepper":
        return _wizard_stepper()
    elif preset == "servo":
        return _wizard_servo()
    elif preset == "i2c":
        return _wizard_i2c()
    elif preset == "spi":
        return _wizard_spi()
    elif preset == "uart":
        return _wizard_uart()

    return 0


def _wizard_motor() -> int:
    """Configure a DC motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]DC Motor Configuration[/bold]")
    console.print("[dim]Requires: PWM pin + 2 direction pins (IN1, IN2)[/dim]")
    console.print()

    motor_id = Prompt.ask("Motor identifier", default="LEFT")
    motor_id = motor_id.upper()

    # Get recommendation from service
    rec = service.recommend_motor_pins(motor_id)

    if rec.warnings:
        for w in rec.warnings:
            print_warning(w)

    # Allow user to override suggestions
    console.print(f"[dim]Suggested pins based on current assignments[/dim]")

    pwm_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_PWM", 0)
    in1_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_IN1", 0)
    in2_default = rec.suggested_assignments.get(f"MOTOR_{motor_id}_IN2", 0)

    pwm_gpio = IntPrompt.ask(f"PWM pin for MOTOR_{motor_id}_PWM", default=pwm_default)
    in1_gpio = IntPrompt.ask(f"IN1 pin for MOTOR_{motor_id}_IN1", default=in1_default)
    in2_gpio = IntPrompt.ask(f"IN2 pin for MOTOR_{motor_id}_IN2", default=in2_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  MOTOR_{motor_id}_PWM = GPIO {pwm_gpio}")
    console.print(f"  MOTOR_{motor_id}_IN1 = GPIO {in1_gpio}")
    console.print(f"  MOTOR_{motor_id}_IN2 = GPIO {in2_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign(f"MOTOR_{motor_id}_PWM", pwm_gpio, force=True)
        _do_assign(f"MOTOR_{motor_id}_IN1", in1_gpio, force=True)
        _do_assign(f"MOTOR_{motor_id}_IN2", in2_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")
    else:
        console.print("[dim]Cancelled.[/dim]")

    return 0


def _wizard_encoder() -> int:
    """Configure a quadrature encoder using PinService recommendations."""
    service = PinService()

    console.print("[bold]Quadrature Encoder Configuration[/bold]")
    console.print("[dim]Requires: 2 input pins (A + B channels)[/dim]")
    console.print()

    enc_id = Prompt.ask("Encoder identifier (e.g., 0, LEFT)", default="0")
    enc_id = enc_id.upper()

    rec = service.recommend_encoder_pins(enc_id)

    a_default = rec.suggested_assignments.get(f"ENC{enc_id}_A", 0)
    b_default = rec.suggested_assignments.get(f"ENC{enc_id}_B", 0)

    a_gpio = IntPrompt.ask(f"A channel pin for ENC{enc_id}_A", default=a_default)
    b_gpio = IntPrompt.ask(f"B channel pin for ENC{enc_id}_B", default=b_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  ENC{enc_id}_A = GPIO {a_gpio}")
    console.print(f"  ENC{enc_id}_B = GPIO {b_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign(f"ENC{enc_id}_A", a_gpio, force=True)
        _do_assign(f"ENC{enc_id}_B", b_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_stepper() -> int:
    """Configure a stepper motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]Stepper Motor Configuration[/bold]")
    console.print("[dim]Requires: STEP, DIR, and optionally EN pins[/dim]")
    console.print()

    stepper_id = Prompt.ask("Stepper identifier", default="0")
    stepper_id = stepper_id.upper()

    rec = service.recommend_stepper_pins(stepper_id)

    step_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_STEP", 0)
    dir_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_DIR", 0)
    en_default = rec.suggested_assignments.get(f"STEPPER{stepper_id}_EN", 0)

    step_gpio = IntPrompt.ask("STEP pin", default=step_default)
    dir_gpio = IntPrompt.ask("DIR pin", default=dir_default)

    use_en = Confirm.ask("Add ENABLE pin?", default=True)
    en_gpio = None
    if use_en:
        en_gpio = IntPrompt.ask("EN pin", default=en_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  STEPPER{stepper_id}_STEP = GPIO {step_gpio}")
    console.print(f"  STEPPER{stepper_id}_DIR = GPIO {dir_gpio}")
    if en_gpio:
        console.print(f"  STEPPER{stepper_id}_EN = GPIO {en_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign(f"STEPPER{stepper_id}_STEP", step_gpio, force=True)
        _do_assign(f"STEPPER{stepper_id}_DIR", dir_gpio, force=True)
        if en_gpio:
            _do_assign(f"STEPPER{stepper_id}_EN", en_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_servo() -> int:
    """Configure a servo motor using PinService recommendations."""
    service = PinService()

    console.print("[bold]Servo Motor Configuration[/bold]")
    console.print("[dim]Requires: 1 PWM-capable pin[/dim]")
    console.print()

    servo_id = Prompt.ask("Servo identifier", default="0")
    servo_id = servo_id.upper()

    rec = service.recommend_servo_pins(servo_id)
    sig_default = rec.suggested_assignments.get(f"SERVO{servo_id}_SIG", 0)

    sig_gpio = IntPrompt.ask("Signal pin", default=sig_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  SERVO{servo_id}_SIG = GPIO {sig_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign(f"SERVO{servo_id}_SIG", sig_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_i2c() -> int:
    """Configure I2C bus using PinService recommendations."""
    service = PinService()

    console.print("[bold]I2C Bus Configuration[/bold]")
    console.print("[dim]Standard pins: GPIO 21 (SDA), GPIO 22 (SCL)[/dim]")
    console.print()

    rec = service.recommend_i2c_pins()

    sda_default = rec.suggested_assignments.get("I2C_SDA", 21)
    scl_default = rec.suggested_assignments.get("I2C_SCL", 22)

    sda_gpio = IntPrompt.ask("SDA pin", default=sda_default)
    scl_gpio = IntPrompt.ask("SCL pin", default=scl_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  I2C_SDA = GPIO {sda_gpio}")
    console.print(f"  I2C_SCL = GPIO {scl_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign("I2C_SDA", sda_gpio, force=True)
        _do_assign("I2C_SCL", scl_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_spi() -> int:
    """Configure SPI bus using PinService recommendations."""
    service = PinService()

    console.print("[bold]SPI Bus Configuration[/bold]")
    console.print("[dim]Standard VSPI pins: MOSI=23, MISO=19, CLK=18, CS=5[/dim]")
    console.print()

    rec = service.recommend_spi_pins()

    mosi_default = rec.suggested_assignments.get("SPI_MOSI", 23)
    miso_default = rec.suggested_assignments.get("SPI_MISO", 19)
    clk_default = rec.suggested_assignments.get("SPI_CLK", 18)
    cs_default = rec.suggested_assignments.get("SPI_CS", 5)

    mosi_gpio = IntPrompt.ask("MOSI pin", default=mosi_default)
    miso_gpio = IntPrompt.ask("MISO pin", default=miso_default)
    clk_gpio = IntPrompt.ask("CLK pin", default=clk_default)
    cs_gpio = IntPrompt.ask("CS pin", default=cs_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  SPI_MOSI = GPIO {mosi_gpio}")
    console.print(f"  SPI_MISO = GPIO {miso_gpio}")
    console.print(f"  SPI_CLK = GPIO {clk_gpio}")
    console.print(f"  SPI_CS = GPIO {cs_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign("SPI_MOSI", mosi_gpio, force=True)
        _do_assign("SPI_MISO", miso_gpio, force=True)
        _do_assign("SPI_CLK", clk_gpio, force=True)
        _do_assign("SPI_CS", cs_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def _wizard_uart() -> int:
    """Configure UART using PinService recommendations."""
    service = PinService()

    console.print("[bold]UART Configuration[/bold]")
    console.print("[dim]UART2 default pins: TX=17, RX=16[/dim]")
    console.print()

    uart_num = Prompt.ask("UART number", default="1")

    rec = service.recommend_uart_pins(uart_num)

    tx_default = rec.suggested_assignments.get(f"UART{uart_num}_TX", 17)
    rx_default = rec.suggested_assignments.get(f"UART{uart_num}_RX", 16)

    tx_gpio = IntPrompt.ask("TX pin", default=tx_default)
    rx_gpio = IntPrompt.ask("RX pin", default=rx_default)

    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  UART{uart_num}_TX = GPIO {tx_gpio}")
    console.print(f"  UART{uart_num}_RX = GPIO {rx_gpio}")
    console.print()

    if Confirm.ask("Apply this configuration?", default=True):
        _do_assign(f"UART{uart_num}_TX", tx_gpio, force=True)
        _do_assign(f"UART{uart_num}_RX", rx_gpio, force=True)
        console.print()
        print_info("Run 'mara generate pins' to regenerate code.")

    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    """Clear all pin assignments."""
    service = PinService()
    pins = service.get_assignments()

    if not pins:
        print_info("No pin assignments to clear.")
        return 0

    console.print()
    console.print(f"[bold yellow]This will remove {len(pins)} pin assignment(s):[/bold yellow]")
    for name, gpio in sorted(pins.items()):
        console.print(f"  {name} = GPIO {gpio}")
    console.print()

    if not args.force:
        if not Confirm.ask("[red]Are you sure?[/red]", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return 0

    success, message = service.clear_all()
    print_success(message)
    console.print()
    print_info("Run 'mara generate pins' to regenerate code.")

    return 0
