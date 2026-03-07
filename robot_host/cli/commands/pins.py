# robot_host/cli/commands/pins.py
"""Pin management commands for MARA CLI."""

import argparse
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from robot_host.cli.console import (
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

# Import pin data from the existing module
from robot_host.tools.pins import (
    ESP32_PINS,
    SAFE_PINS,
    INPUT_ONLY_PINS,
    FLASH_PINS,
    BOOT_PINS,
    PINS_JSON,
    Capability,
    PinInfo,
    load_pins,
    save_pins,
    get_assignments,
    cap_str,
    generate_pinout,
)

# Pin groups that should be used together
PIN_GROUPS = {
    "i2c": {
        "pins": ["I2C_SDA", "I2C_SCL"],
        "default_gpios": [21, 22],
        "description": "I2C bus (SDA + SCL)",
    },
    "spi": {
        "pins": ["SPI_MOSI", "SPI_MISO", "SPI_CLK", "SPI_CS"],
        "default_gpios": [23, 19, 18, 5],
        "description": "SPI bus (MOSI, MISO, CLK, CS)",
    },
    "uart": {
        "pins": ["UART_TX", "UART_RX"],
        "default_gpios": [17, 16],
        "description": "UART (TX + RX)",
    },
    "motor": {
        "pins": ["MOTOR_{}_PWM", "MOTOR_{}_IN1", "MOTOR_{}_IN2"],
        "description": "DC Motor (PWM + direction pins)",
    },
    "encoder": {
        "pins": ["ENC{}_A", "ENC{}_B"],
        "description": "Quadrature encoder (A + B channels)",
    },
    "stepper": {
        "pins": ["STEPPER{}_STEP", "STEPPER{}_DIR", "STEPPER{}_EN"],
        "description": "Stepper motor (STEP, DIR, EN)",
    },
}


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
    pinout_text = generate_pinout()

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
    assignments = get_assignments()
    all_gpios = sorted(ESP32_PINS.keys())

    console.print()
    console.print("[bold cyan]ESP32 GPIO Pin Status[/bold cyan]")
    console.print()

    table = create_pin_table()

    for gpio in all_gpios:
        if gpio not in ESP32_PINS:
            continue
        info = ESP32_PINS[gpio]

        # Status with styling
        status_text, status_style = format_pin_status(
            gpio=gpio,
            assigned_name=assignments.get(gpio),
            is_flash=gpio in FLASH_PINS,
            is_boot=gpio in BOOT_PINS,
            is_input_only=gpio in INPUT_ONLY_PINS,
            has_warning=bool(info.warning),
        )

        # Capabilities
        caps = cap_str(info.capabilities)

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
    used = len(assignments)
    usable = len([g for g in ESP32_PINS if g not in FLASH_PINS])
    console.print()
    console.print(f"[dim]Assigned: {used}/{usable} usable pins[/dim]")
    console.print(f"[dim]Safe pins available: {len(SAFE_PINS - set(assignments.keys()))}[/dim]")

    return 0


def cmd_free(args: argparse.Namespace) -> int:
    """Show only available pins."""
    assignments = get_assignments()
    assigned_gpios = set(assignments.keys())

    console.print()
    console.print("[bold cyan]Available GPIO Pins[/bold cyan]")
    console.print()

    def print_pin_section(title: str, gpios: set[int], style: str = "white") -> None:
        """Print a section of pins."""
        free_gpios = sorted(gpios - assigned_gpios)
        if not free_gpios:
            return

        console.print(f"[bold {style}]{title}[/bold {style}]")
        table = create_pin_table()

        for gpio in free_gpios:
            if gpio not in ESP32_PINS:
                continue
            info = ESP32_PINS[gpio]
            status_text, status_style = format_pin_status(
                gpio=gpio,
                assigned_name=None,
                is_flash=gpio in FLASH_PINS,
                is_boot=gpio in BOOT_PINS,
                is_input_only=gpio in INPUT_ONLY_PINS,
                has_warning=bool(info.warning),
            )
            table.add_row(
                str(gpio),
                f"[{status_style}]{status_text}[/{status_style}]",
                cap_str(info.capabilities),
                info.notes[:40],
            )

        console.print(table)
        console.print()

    # Recommended (safe) pins first
    print_pin_section("RECOMMENDED (no boot/flash restrictions)", SAFE_PINS, "green")

    # Input-only pins
    print_pin_section("INPUT-ONLY PINS (GPIO 34-39, no output/PWM)", INPUT_ONLY_PINS, "blue")

    # Boot pins (usable with caution)
    boot_usable = (BOOT_PINS - FLASH_PINS)
    print_pin_section("BOOT PINS (usable but check warnings)", boot_usable, "yellow")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed info for a specific pin."""
    gpio = args.gpio

    if gpio not in ESP32_PINS:
        print_error(f"GPIO {gpio} not found in ESP32 pinout")
        return 1

    info = ESP32_PINS[gpio]
    assignments = get_assignments()

    console.print()
    console.print(f"[bold cyan]GPIO {gpio}[/bold cyan]")
    console.print()

    # Status
    if gpio in assignments:
        console.print(f"[bold]Status:[/bold]       [green]ASSIGNED as '{assignments[gpio]}'[/green]")
    elif gpio in FLASH_PINS:
        console.print(f"[bold]Status:[/bold]       [red]UNUSABLE (connected to flash)[/red]")
    else:
        console.print(f"[bold]Status:[/bold]       [cyan]Available[/cyan]")

    console.print(f"[bold]Capabilities:[/bold] {cap_str(info.capabilities)}")
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

    if gpio in SAFE_PINS:
        console.print()
        print_success("This is a safe, recommended pin for general use.")

    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    """Assign a name to a GPIO pin."""
    name = args.name.upper()
    gpio = args.gpio

    # Validate GPIO
    if gpio not in ESP32_PINS:
        print_error(f"GPIO {gpio} not found in ESP32 pinout")
        return 1

    if gpio in FLASH_PINS:
        print_error(f"GPIO {gpio} is connected to flash and cannot be used")
        return 1

    pins = load_pins()
    assignments = get_assignments()

    # Check if name already used
    if name in pins:
        print_error(f"Name '{name}' already assigned to GPIO {pins[name]}")
        return 1

    # Check if GPIO already assigned
    if gpio in assignments:
        print_error(f"GPIO {gpio} already assigned as '{assignments[gpio]}'")
        return 1

    # Warnings for boot pins
    info = ESP32_PINS[gpio]
    if info.warning and not args.force:
        print_warning(info.warning)
        if not confirm("Continue anyway?"):
            console.print("[dim]Cancelled.[/dim]")
            return 0

    # Assign
    pins[name] = gpio
    save_pins(pins)
    print_success(f"Assigned {name} = GPIO {gpio}")
    console.print()
    print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")

    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    """Remove a pin assignment."""
    name = args.name.upper()
    pins = load_pins()

    if name not in pins:
        print_error(f"'{name}' not found in pin assignments")
        return 1

    gpio = pins.pop(name)
    save_pins(pins)
    print_success(f"Removed {name} (was GPIO {gpio})")
    console.print()
    print_info("Run 'mara generate pins' or 'mara generate all' to regenerate code.")

    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    """Suggest best pins for a specific use case."""
    use_case = args.use_case
    assignments = get_assignments()
    assigned_gpios = set(assignments.keys())

    # Map use cases to required capabilities
    use_map = {
        "pwm": Capability.PWM | Capability.OUTPUT,
        "adc": Capability.ADC,
        "input": Capability.INPUT,
        "output": Capability.OUTPUT,
        "i2c": Capability.I2C,
        "spi": Capability.SPI,
        "uart": Capability.UART,
        "touch": Capability.TOUCH,
        "dac": Capability.DAC,
    }

    required = use_map[use_case]

    console.print()
    console.print(f"[bold cyan]Best pins for {use_case.upper()}[/bold cyan]")
    console.print()

    # Find matching pins, prioritize safe pins
    candidates = []
    for gpio, info in ESP32_PINS.items():
        if gpio in assigned_gpios or gpio in FLASH_PINS:
            continue
        if (info.capabilities & required) == required:
            priority = 0 if gpio in SAFE_PINS else (1 if not info.warning else 2)
            candidates.append((priority, gpio))

    candidates.sort()

    if not candidates:
        print_warning("No available pins match this use case.")
        return 0

    table = create_pin_table()
    for _, gpio in candidates[:10]:
        info = ESP32_PINS[gpio]
        status_text, status_style = format_pin_status(
            gpio=gpio,
            assigned_name=None,
            is_flash=False,
            is_boot=gpio in BOOT_PINS,
            is_input_only=gpio in INPUT_ONLY_PINS,
            has_warning=bool(info.warning),
        )
        table.add_row(
            str(gpio),
            f"[{status_style}]{status_text}[/{status_style}]",
            cap_str(info.capabilities),
            info.notes[:40],
        )

    console.print(table)

    # Special notes
    console.print()
    if use_case == "adc":
        print_info("ADC2 pins (GPIO 0,2,4,12-15,25-27) don't work when WiFi is active.")
        print_info("ADC1 pins (GPIO 32-39) work with WiFi.")
    elif use_case == "i2c":
        print_info("Default I2C pins are GPIO 21 (SDA) and 22 (SCL).")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate current pin assignments for issues."""
    pins = load_pins()
    issues = []
    warnings = []

    for name, gpio in pins.items():
        if gpio not in ESP32_PINS:
            issues.append((name, gpio, "Invalid GPIO number"))
            continue

        info = ESP32_PINS[gpio]

        if gpio in FLASH_PINS:
            issues.append((name, gpio, "Connected to flash, unusable!"))

        if info.warning:
            warnings.append((name, gpio, info.warning))

    console.print()
    console.print("[bold cyan]Pin Assignment Validation[/bold cyan]")
    console.print()

    if issues:
        console.print("[bold red]ERRORS:[/bold red]")
        for name, gpio, msg in issues:
            console.print(f"  [red]\u2717[/red] {name} (GPIO {gpio}): {msg}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for name, gpio, msg in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  {name} (GPIO {gpio}): {msg}")
        console.print()

    if not issues and not warnings:
        print_success("All pin assignments look good!")
        console.print()

    console.print(f"[dim]Total: {len(pins)} pins assigned[/dim]")

    return 1 if issues else 0


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
    if gpio not in ESP32_PINS:
        print_error(f"GPIO {gpio} not found in ESP32 pinout")
        return False

    if gpio in FLASH_PINS:
        print_error(f"GPIO {gpio} is connected to flash and cannot be used")
        return False

    pins = load_pins()
    assignments = get_assignments()

    if name in pins:
        print_error(f"Name '{name}' already assigned to GPIO {pins[name]}")
        return False

    if gpio in assignments:
        print_error(f"GPIO {gpio} already assigned as '{assignments[gpio]}'")
        return False

    info = ESP32_PINS[gpio]
    if info.warning and not force:
        print_warning(info.warning)
        if not Confirm.ask("Continue anyway?", default=False):
            console.print("[dim]Cancelled.[/dim]")
            return False

    pins[name] = gpio
    save_pins(pins)
    print_success(f"Assigned {name} = GPIO {gpio}")
    return True


def _do_remove(name: str) -> bool:
    """Remove a pin assignment (helper for interactive mode)."""
    pins = load_pins()

    if name not in pins:
        print_error(f"'{name}' not found in pin assignments")
        return False

    gpio = pins.pop(name)
    save_pins(pins)
    print_success(f"Removed {name} (was GPIO {gpio})")
    return True


def cmd_conflicts(args: argparse.Namespace) -> int:
    """Check for pin conflicts and potential issues."""
    pins = load_pins()
    assignments = get_assignments()
    conflicts = []
    warnings = []

    console.print()
    console.print("[bold cyan]Pin Conflict Analysis[/bold cyan]")
    console.print()

    # Check for I2C conflicts
    i2c_sda = None
    i2c_scl = None
    for name, gpio in pins.items():
        if "SDA" in name.upper():
            i2c_sda = (name, gpio)
        if "SCL" in name.upper():
            i2c_scl = (name, gpio)

    if i2c_sda and not i2c_scl:
        warnings.append(("I2C Incomplete", f"SDA assigned ({i2c_sda[0]}=GPIO{i2c_sda[1]}) but SCL missing"))
    if i2c_scl and not i2c_sda:
        warnings.append(("I2C Incomplete", f"SCL assigned ({i2c_scl[0]}=GPIO{i2c_scl[1]}) but SDA missing"))

    # Check for UART conflicts
    uart_pins = {}
    for name, gpio in pins.items():
        if "UART" in name.upper() or "TX" in name.upper() or "RX" in name.upper():
            # Extract UART number if present
            for i in range(3):
                if f"UART{i}" in name.upper() or f"UART_{i}" in name.upper():
                    if i not in uart_pins:
                        uart_pins[i] = {}
                    if "TX" in name.upper():
                        uart_pins[i]["tx"] = (name, gpio)
                    if "RX" in name.upper():
                        uart_pins[i]["rx"] = (name, gpio)

    for uart_num, pins_dict in uart_pins.items():
        if "tx" in pins_dict and "rx" not in pins_dict:
            warnings.append((f"UART{uart_num} Incomplete", f"TX assigned but RX missing"))
        if "rx" in pins_dict and "tx" not in pins_dict:
            warnings.append((f"UART{uart_num} Incomplete", f"RX assigned but TX missing"))

    # Check for motor/encoder pairing
    motors = set()
    encoders = set()
    for name in pins.keys():
        if "MOTOR" in name.upper():
            # Extract motor identifier
            for part in name.upper().replace("_", " ").split():
                if part not in ("MOTOR", "PWM", "IN1", "IN2", "DIR", "EN"):
                    motors.add(part)
        if "ENC" in name.upper() or "ENCODER" in name.upper():
            for part in name.upper().replace("_", " ").split():
                if part not in ("ENC", "ENCODER", "A", "B"):
                    encoders.add(part)

    # Check for ADC2 + WiFi conflict potential
    adc2_pins = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}
    adc2_assigned = []
    for name, gpio in pins.items():
        if gpio in adc2_pins and "ADC" in name.upper():
            adc2_assigned.append((name, gpio))

    if adc2_assigned:
        warnings.append((
            "ADC2 + WiFi",
            f"ADC2 pins assigned ({', '.join(f'{n}=GPIO{g}' for n, g in adc2_assigned)}). "
            "These won't work when WiFi is active."
        ))

    # Check for boot pin usage
    boot_assigned = []
    for name, gpio in pins.items():
        if gpio in BOOT_PINS:
            info = ESP32_PINS[gpio]
            boot_assigned.append((name, gpio, info.warning))

    # Display results
    if conflicts:
        console.print("[bold red]CONFLICTS:[/bold red]")
        for title, msg in conflicts:
            console.print(f"  [red]\u2717[/red] [bold]{title}:[/bold] {msg}")
        console.print()

    if warnings:
        console.print("[bold yellow]WARNINGS:[/bold yellow]")
        for title, msg in warnings:
            console.print(f"  [yellow]\u26a0[/yellow]  [bold]{title}:[/bold] {msg}")
        console.print()

    if boot_assigned:
        console.print("[bold yellow]BOOT PINS IN USE:[/bold yellow]")
        for name, gpio, warning in boot_assigned:
            console.print(f"  [yellow]\u26a0[/yellow]  {name} (GPIO {gpio})")
            console.print(f"      [dim]{warning}[/dim]")
        console.print()

    if not conflicts and not warnings and not boot_assigned:
        print_success("No conflicts or issues detected!")
        console.print()

    # Summary
    console.print(f"[dim]Analyzed {len(pins)} pin assignments[/dim]")

    return 1 if conflicts else 0


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


def _get_available_pins(required_caps: Capability = Capability.NONE) -> list[int]:
    """Get list of available pins with required capabilities."""
    assignments = get_assignments()
    available = []

    for gpio, info in ESP32_PINS.items():
        if gpio in assignments or gpio in FLASH_PINS:
            continue
        if required_caps and not (info.capabilities & required_caps) == required_caps:
            continue
        available.append(gpio)

    # Sort: safe pins first, then by GPIO number
    return sorted(available, key=lambda g: (0 if g in SAFE_PINS else 1, g))


def _wizard_motor() -> int:
    """Configure a DC motor."""
    console.print("[bold]DC Motor Configuration[/bold]")
    console.print("[dim]Requires: PWM pin + 2 direction pins (IN1, IN2)[/dim]")
    console.print()

    # Get motor identifier
    motor_id = Prompt.ask("Motor identifier", default="LEFT")
    motor_id = motor_id.upper()

    # Get available PWM pins
    pwm_pins = _get_available_pins(Capability.PWM | Capability.OUTPUT)
    if not pwm_pins:
        print_error("No PWM-capable pins available!")
        return 1

    console.print(f"[dim]Available PWM pins: {', '.join(map(str, pwm_pins[:10]))}[/dim]")
    pwm_gpio = IntPrompt.ask(f"PWM pin for MOTOR_{motor_id}_PWM", default=pwm_pins[0])

    # Get direction pins
    dir_pins = _get_available_pins(Capability.OUTPUT)
    dir_pins = [p for p in dir_pins if p != pwm_gpio]

    console.print(f"[dim]Available direction pins: {', '.join(map(str, dir_pins[:10]))}[/dim]")
    in1_gpio = IntPrompt.ask(f"IN1 pin for MOTOR_{motor_id}_IN1", default=dir_pins[0] if dir_pins else 0)
    dir_pins = [p for p in dir_pins if p != in1_gpio]
    in2_gpio = IntPrompt.ask(f"IN2 pin for MOTOR_{motor_id}_IN2", default=dir_pins[0] if dir_pins else 0)

    # Confirm and assign
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
    """Configure a quadrature encoder."""
    console.print("[bold]Quadrature Encoder Configuration[/bold]")
    console.print("[dim]Requires: 2 input pins (A + B channels)[/dim]")
    console.print()

    enc_id = Prompt.ask("Encoder identifier (e.g., 0, LEFT)", default="0")
    enc_id = enc_id.upper()

    input_pins = _get_available_pins(Capability.INPUT)
    console.print(f"[dim]Available input pins: {', '.join(map(str, input_pins[:10]))}[/dim]")

    a_gpio = IntPrompt.ask(f"A channel pin for ENC{enc_id}_A", default=input_pins[0] if input_pins else 0)
    input_pins = [p for p in input_pins if p != a_gpio]
    b_gpio = IntPrompt.ask(f"B channel pin for ENC{enc_id}_B", default=input_pins[0] if input_pins else 0)

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
    """Configure a stepper motor."""
    console.print("[bold]Stepper Motor Configuration[/bold]")
    console.print("[dim]Requires: STEP, DIR, and optionally EN pins[/dim]")
    console.print()

    stepper_id = Prompt.ask("Stepper identifier", default="0")
    stepper_id = stepper_id.upper()

    output_pins = _get_available_pins(Capability.OUTPUT)
    console.print(f"[dim]Available output pins: {', '.join(map(str, output_pins[:10]))}[/dim]")

    step_gpio = IntPrompt.ask(f"STEP pin", default=output_pins[0] if output_pins else 0)
    output_pins = [p for p in output_pins if p != step_gpio]
    dir_gpio = IntPrompt.ask(f"DIR pin", default=output_pins[0] if output_pins else 0)
    output_pins = [p for p in output_pins if p != dir_gpio]

    use_en = Confirm.ask("Add ENABLE pin?", default=True)
    en_gpio = None
    if use_en:
        en_gpio = IntPrompt.ask(f"EN pin", default=output_pins[0] if output_pins else 0)

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
    """Configure a servo motor."""
    console.print("[bold]Servo Motor Configuration[/bold]")
    console.print("[dim]Requires: 1 PWM-capable pin[/dim]")
    console.print()

    servo_id = Prompt.ask("Servo identifier", default="0")
    servo_id = servo_id.upper()

    pwm_pins = _get_available_pins(Capability.PWM | Capability.OUTPUT)
    console.print(f"[dim]Available PWM pins: {', '.join(map(str, pwm_pins[:10]))}[/dim]")

    sig_gpio = IntPrompt.ask(f"Signal pin", default=pwm_pins[0] if pwm_pins else 0)

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
    """Configure I2C bus."""
    console.print("[bold]I2C Bus Configuration[/bold]")
    console.print("[dim]Standard pins: GPIO 21 (SDA), GPIO 22 (SCL)[/dim]")
    console.print()

    i2c_pins = _get_available_pins(Capability.I2C)

    # Default to standard I2C pins if available
    default_sda = 21 if 21 in i2c_pins else (i2c_pins[0] if i2c_pins else 0)
    default_scl = 22 if 22 in i2c_pins else (i2c_pins[1] if len(i2c_pins) > 1 else 0)

    console.print(f"[dim]Available I2C-capable pins: {', '.join(map(str, i2c_pins))}[/dim]")

    sda_gpio = IntPrompt.ask("SDA pin", default=default_sda)
    scl_gpio = IntPrompt.ask("SCL pin", default=default_scl)

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
    """Configure SPI bus."""
    console.print("[bold]SPI Bus Configuration[/bold]")
    console.print("[dim]Standard VSPI pins: MOSI=23, MISO=19, CLK=18, CS=5[/dim]")
    console.print()

    spi_pins = _get_available_pins(Capability.SPI)
    output_pins = _get_available_pins(Capability.OUTPUT)

    console.print(f"[dim]Available SPI-capable pins: {', '.join(map(str, spi_pins))}[/dim]")

    mosi_gpio = IntPrompt.ask("MOSI pin", default=23 if 23 in spi_pins else (spi_pins[0] if spi_pins else 0))
    miso_gpio = IntPrompt.ask("MISO pin", default=19 if 19 in spi_pins else 0)
    clk_gpio = IntPrompt.ask("CLK pin", default=18 if 18 in spi_pins else 0)
    cs_gpio = IntPrompt.ask("CS pin", default=5 if 5 in output_pins else 0)

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
    """Configure UART."""
    console.print("[bold]UART Configuration[/bold]")
    console.print("[dim]UART2 default pins: TX=17, RX=16[/dim]")
    console.print()

    uart_num = Prompt.ask("UART number", default="1")

    uart_pins = _get_available_pins(Capability.UART)
    console.print(f"[dim]Available UART-capable pins: {', '.join(map(str, uart_pins))}[/dim]")

    tx_gpio = IntPrompt.ask("TX pin", default=17 if 17 in uart_pins else (uart_pins[0] if uart_pins else 0))
    rx_gpio = IntPrompt.ask("RX pin", default=16 if 16 in uart_pins else 0)

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
    pins = load_pins()

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

    save_pins({})
    print_success(f"Cleared {len(pins)} pin assignment(s)")
    console.print()
    print_info("Run 'mara generate pins' to regenerate code.")

    return 0
