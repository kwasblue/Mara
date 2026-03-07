# robot_host/cli/commands/config.py
"""Configuration management commands for MARA CLI."""

import argparse
from pathlib import Path

from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register config commands."""
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Manage robot configuration files",
    )

    config_sub = config_parser.add_subparsers(
        dest="config_cmd",
        title="config commands",
        metavar="<subcommand>",
    )

    # show
    show_p = config_sub.add_parser(
        "show",
        help="Show current configuration",
    )
    show_p.add_argument(
        "path",
        nargs="?",
        help="Config file path (default: searches standard locations)",
    )
    show_p.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    show_p.set_defaults(func=cmd_show)

    # validate
    validate_p = config_sub.add_parser(
        "validate",
        help="Validate configuration files",
    )
    validate_p.add_argument(
        "path",
        nargs="?",
        help="Config file to validate",
    )
    validate_p.set_defaults(func=cmd_validate)

    # init
    init_p = config_sub.add_parser(
        "init",
        help="Initialize new robot configuration",
    )
    init_p.add_argument(
        "name",
        help="Robot name",
    )
    init_p.add_argument(
        "-d", "--directory",
        default="robots",
        help="Output directory (default: robots/)",
    )
    init_p.add_argument(
        "--template",
        choices=["minimal", "differential", "full"],
        default="minimal",
        help="Configuration template (default: minimal)",
    )
    init_p.set_defaults(func=cmd_init)

    # cli - CLI configuration
    cli_p = config_sub.add_parser(
        "cli",
        help="Show or edit CLI defaults (~/.mara.yaml)",
    )
    cli_p.add_argument(
        "--init",
        action="store_true",
        help="Create default CLI config file",
    )
    cli_p.add_argument(
        "--edit",
        action="store_true",
        help="Open CLI config in editor",
    )
    cli_p.set_defaults(func=cmd_cli)

    # Default
    config_parser.set_defaults(func=cmd_show)


def _find_config_files() -> list[Path]:
    """Find configuration files in standard locations."""
    locations = [
        Path("robot.yaml"),
        Path("robot.yml"),
        Path("config/robot.yaml"),
        Path("robots"),
    ]

    found = []
    for loc in locations:
        if loc.is_file():
            found.append(loc)
        elif loc.is_dir():
            found.extend(loc.glob("*.yaml"))
            found.extend(loc.glob("*.yml"))

    return found


def cmd_show(args: argparse.Namespace) -> int:
    """Show current configuration."""
    path = getattr(args, 'path', None)
    as_json = getattr(args, 'json', False)

    if path:
        config_file = Path(path)
        if not config_file.exists():
            print_error(f"Config file not found: {path}")
            return 1
        files = [config_file]
    else:
        files = _find_config_files()
        if not files:
            print_warning("No configuration files found")
            print_info("Create one with: mara config init <robot_name>")
            return 0

    console.print()

    for config_file in files:
        console.print(f"[bold cyan]{config_file}[/bold cyan]")
        console.print()

        content = config_file.read_text()

        if as_json:
            import yaml
            import json
            data = yaml.safe_load(content)
            console.print(json.dumps(data, indent=2))
        else:
            syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
            console.print(syntax)

        console.print()

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate configuration files."""
    path = getattr(args, 'path', None)

    if path:
        files = [Path(path)]
    else:
        files = _find_config_files()
        if not files:
            print_warning("No configuration files found")
            return 0

    console.print()
    console.print("[bold cyan]Validating Configuration[/bold cyan]")
    console.print()

    errors = 0

    for config_file in files:
        console.print(f"  {config_file}...", end=" ")

        if not config_file.exists():
            console.print("[red]not found[/red]")
            errors += 1
            continue

        try:
            from robot_host.config.robot_config import RobotConfig

            config = RobotConfig.load(str(config_file))
            validation_errors = config.validate()

            if validation_errors:
                console.print("[red]invalid[/red]")
                for err in validation_errors:
                    console.print(f"    [red]\u2717[/red] {err}")
                errors += 1
            else:
                console.print("[green]valid[/green]")

        except Exception as e:
            console.print(f"[red]error[/red]")
            console.print(f"    [red]{e}[/red]")
            errors += 1

    console.print()
    if errors == 0:
        print_success(f"All {len(files)} configuration(s) valid")
    else:
        print_error(f"{errors} configuration(s) invalid")

    return 1 if errors > 0 else 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize new robot configuration."""
    name = args.name
    directory = Path(args.directory)
    template = args.template

    # Create directory
    directory.mkdir(parents=True, exist_ok=True)

    # Generate config file
    config_file = directory / f"{name}.yaml"

    if config_file.exists():
        print_error(f"Config file already exists: {config_file}")
        return 1

    console.print()
    console.print("[bold cyan]Initializing Robot Configuration[/bold cyan]")
    console.print(f"  Name: [green]{name}[/green]")
    console.print(f"  Template: [yellow]{template}[/yellow]")
    console.print(f"  Output: [yellow]{config_file}[/yellow]")
    console.print()

    # Generate template
    if template == "minimal":
        content = _template_minimal(name)
    elif template == "differential":
        content = _template_differential(name)
    else:
        content = _template_full(name)

    config_file.write_text(content)
    print_success(f"Created: {config_file}")

    console.print()
    print_info("Next steps:")
    console.print("  1. Edit the configuration file with your robot's settings")
    console.print("  2. Run 'mara config validate' to check for errors")
    console.print("  3. Use 'mara run serial' or 'mara run tcp' to connect")

    return 0


def _template_minimal(name: str) -> str:
    """Generate minimal configuration template."""
    return f"""# Robot configuration: {name}
# Generated by: mara config init

robot:
  name: {name}
  version: "1.0.0"

transport:
  type: serial
  port: /dev/cu.usbserial-0001
  baudrate: 115200

# Uncomment and configure as needed:
# pins:
#   LED: 2
#   BUTTON: 0

# modules: []
"""


def _template_differential(name: str) -> str:
    """Generate differential drive configuration template."""
    return f"""# Robot configuration: {name}
# Differential drive robot template
# Generated by: mara config init

robot:
  name: {name}
  version: "1.0.0"
  type: differential_drive

transport:
  type: serial
  port: /dev/cu.usbserial-0001
  baudrate: 115200

pins:
  # Motor pins
  MOTOR_LEFT_PWM: 25
  MOTOR_LEFT_DIR: 26
  MOTOR_RIGHT_PWM: 27
  MOTOR_RIGHT_DIR: 14

  # Encoder pins
  ENCODER_LEFT_A: 32
  ENCODER_LEFT_B: 33
  ENCODER_RIGHT_A: 34
  ENCODER_RIGHT_B: 35

  # Other
  LED: 2

drive:
  wheel_diameter_m: 0.065
  wheel_base_m: 0.15
  encoder_ticks_per_rev: 480
  max_speed_mps: 0.5

motors:
  left:
    pwm_channel: 0
    pwm_pin: MOTOR_LEFT_PWM
    dir_pin: MOTOR_LEFT_DIR
    inverted: false

  right:
    pwm_channel: 1
    pwm_pin: MOTOR_RIGHT_PWM
    dir_pin: MOTOR_RIGHT_DIR
    inverted: true

encoders:
  left:
    channel: 0
    pin_a: ENCODER_LEFT_A
    pin_b: ENCODER_LEFT_B

  right:
    channel: 1
    pin_a: ENCODER_RIGHT_A
    pin_b: ENCODER_RIGHT_B
"""


def _template_full(name: str) -> str:
    """Generate full configuration template."""
    return f"""# Robot configuration: {name}
# Full robot template with all features
# Generated by: mara config init

robot:
  name: {name}
  version: "1.0.0"
  type: full

transport:
  type: tcp
  host: 192.168.4.1
  port: 3333

# Alternative: serial transport
# transport:
#   type: serial
#   port: /dev/cu.usbserial-0001
#   baudrate: 115200

pins:
  # Motors
  MOTOR_LEFT_PWM: 25
  MOTOR_LEFT_DIR: 26
  MOTOR_RIGHT_PWM: 27
  MOTOR_RIGHT_DIR: 14

  # Encoders
  ENCODER_LEFT_A: 32
  ENCODER_LEFT_B: 33
  ENCODER_RIGHT_A: 34
  ENCODER_RIGHT_B: 35

  # Servos
  SERVO_PAN: 18
  SERVO_TILT: 19

  # Sensors
  ULTRASONIC_TRIG: 21
  ULTRASONIC_ECHO: 22

  # I2C (IMU)
  I2C_SDA: 21
  I2C_SCL: 22

  # Other
  LED: 2
  BUTTON: 0

drive:
  wheel_diameter_m: 0.065
  wheel_base_m: 0.15
  encoder_ticks_per_rev: 480
  max_speed_mps: 0.5

motors:
  left:
    pwm_channel: 0
    pwm_pin: MOTOR_LEFT_PWM
    dir_pin: MOTOR_LEFT_DIR
    inverted: false

  right:
    pwm_channel: 1
    pwm_pin: MOTOR_RIGHT_PWM
    dir_pin: MOTOR_RIGHT_DIR
    inverted: true

encoders:
  left:
    channel: 0
    pin_a: ENCODER_LEFT_A
    pin_b: ENCODER_LEFT_B

  right:
    channel: 1
    pin_a: ENCODER_RIGHT_A
    pin_b: ENCODER_RIGHT_B

servos:
  pan:
    channel: 0
    pin: SERVO_PAN
    min_angle: 0
    max_angle: 180
    center_angle: 90

  tilt:
    channel: 1
    pin: SERVO_TILT
    min_angle: 0
    max_angle: 90
    center_angle: 45

sensors:
  ultrasonic:
    trig_pin: ULTRASONIC_TRIG
    echo_pin: ULTRASONIC_ECHO
    max_distance_m: 4.0

  imu:
    type: MPU6050
    address: 0x68

control:
  tick_hz: 50
  pid:
    kp: 1.0
    ki: 0.1
    kd: 0.05

runtime:
  tick_hz: 50
  watchdog_timeout_s: 2.0
  telemetry_hz: 10
"""


def cmd_cli(args: argparse.Namespace) -> int:
    """Show or edit CLI configuration."""
    from robot_host.cli import cli_config

    init_config = getattr(args, 'init', False)
    edit = getattr(args, 'edit', False)

    console.print()
    console.print("[bold cyan]CLI Configuration[/bold cyan]")
    console.print()

    # Find existing config
    config_file = cli_config.find_config_file()

    if init_config:
        if config_file:
            print_warning(f"Config already exists: {config_file}")
            from rich.prompt import Confirm
            if not Confirm.ask("Overwrite?", default=False):
                return 0

        new_file = cli_config.init_config()
        print_success(f"Created: {new_file}")
        return 0

    if not config_file:
        print_info("No CLI config file found")
        console.print()
        console.print("Create one with:")
        console.print("  [cyan]mara config cli --init[/cyan]")
        console.print()
        console.print("Or create ~/.mara.yaml manually with:")
        console.print()
        console.print(Syntax(cli_config.create_default_config(), "yaml", theme="monokai"))
        return 0

    if edit:
        import os
        import subprocess

        editor = cli_config.get("editor") or os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(config_file)])
        return 0

    # Show current config
    console.print(f"  Location: [green]{config_file}[/green]")
    console.print()

    content = config_file.read_text()
    syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)

    return 0
