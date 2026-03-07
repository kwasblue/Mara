# robot_host/cli/completions.py
"""Shell completion generation for MARA CLI."""

import argparse
from pathlib import Path

from robot_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register completions command."""
    comp_parser = subparsers.add_parser(
        "completions",
        help="Generate shell completions",
        description="Generate shell completion scripts for bash, zsh, or fish",
    )

    comp_parser.add_argument(
        "shell",
        choices=["bash", "zsh", "fish"],
        help="Shell type",
    )
    comp_parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)",
    )
    comp_parser.add_argument(
        "--install",
        action="store_true",
        help="Install completions to appropriate location",
    )

    comp_parser.set_defaults(func=cmd_completions)


def cmd_completions(args: argparse.Namespace) -> int:
    """Generate shell completions."""
    shell = args.shell
    output = args.output
    install = args.install

    if shell == "bash":
        script = _generate_bash()
    elif shell == "zsh":
        script = _generate_zsh()
    elif shell == "fish":
        script = _generate_fish()
    else:
        print_error(f"Unknown shell: {shell}")
        return 1

    if install:
        return _install_completions(shell, script)
    elif output:
        Path(output).write_text(script)
        print_success(f"Completions written to {output}")
    else:
        console.print(script)

    return 0


def _generate_bash() -> str:
    """Generate bash completions."""
    return '''# MARA CLI bash completions
# Add to ~/.bashrc or ~/.bash_completion

_mara_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Top-level commands
    local commands="pins build generate run record replay config dashboard flash monitor calibrate test logs sim version completions"

    # Subcommands
    local pins_cmds="pinout list free info assign remove suggest validate interactive conflicts wizard clear"
    local build_cmds="compile upload clean test features size watch"
    local generate_cmds="all commands pins can telemetry binary gpio"
    local run_cmds="serial tcp can mqtt shell"
    local config_cmds="show validate init"
    local flash_cmds="auto ports erase info"
    local calibrate_cmds="motor encoder imu servo wheels"
    local test_cmds="all connection motors encoders servos sensors gpio"
    local logs_cmds="list show tail search stats delete export"
    local sim_cmds="virtual replay loopback"

    case "${prev}" in
        mara)
            COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
            return 0
            ;;
        pins)
            COMPREPLY=( $(compgen -W "${pins_cmds}" -- ${cur}) )
            return 0
            ;;
        build)
            COMPREPLY=( $(compgen -W "${build_cmds}" -- ${cur}) )
            return 0
            ;;
        generate)
            COMPREPLY=( $(compgen -W "${generate_cmds}" -- ${cur}) )
            return 0
            ;;
        run)
            COMPREPLY=( $(compgen -W "${run_cmds}" -- ${cur}) )
            return 0
            ;;
        config)
            COMPREPLY=( $(compgen -W "${config_cmds}" -- ${cur}) )
            return 0
            ;;
        flash)
            COMPREPLY=( $(compgen -W "${flash_cmds}" -- ${cur}) )
            return 0
            ;;
        calibrate)
            COMPREPLY=( $(compgen -W "${calibrate_cmds}" -- ${cur}) )
            return 0
            ;;
        test)
            COMPREPLY=( $(compgen -W "${test_cmds}" -- ${cur}) )
            return 0
            ;;
        logs)
            COMPREPLY=( $(compgen -W "${logs_cmds}" -- ${cur}) )
            return 0
            ;;
        sim)
            COMPREPLY=( $(compgen -W "${sim_cmds}" -- ${cur}) )
            return 0
            ;;
        -p|--port)
            # Complete serial ports
            COMPREPLY=( $(compgen -f /dev/cu.usb* /dev/ttyUSB* -- ${cur}) )
            return 0
            ;;
        -e|--env)
            local envs="esp32_minimal esp32_motors esp32_sensors esp32_control esp32_full esp32_usb esp32_ota esp32_base native esp32_test"
            COMPREPLY=( $(compgen -W "${envs}" -- ${cur}) )
            return 0
            ;;
        --preset)
            local presets="minimal motors sensors control full"
            COMPREPLY=( $(compgen -W "${presets}" -- ${cur}) )
            return 0
            ;;
        suggest)
            local use_cases="pwm adc input output i2c spi uart touch dac"
            COMPREPLY=( $(compgen -W "${use_cases}" -- ${cur}) )
            return 0
            ;;
        wizard)
            local wizards="motor encoder stepper servo i2c spi uart"
            COMPREPLY=( $(compgen -W "${wizards}" -- ${cur}) )
            return 0
            ;;
    esac

    # Default: complete flags
    if [[ ${cur} == -* ]]; then
        local flags="-h --help -v --verbose"
        COMPREPLY=( $(compgen -W "${flags}" -- ${cur}) )
        return 0
    fi
}

complete -F _mara_completions mara
'''


def _generate_zsh() -> str:
    """Generate zsh completions."""
    return '''#compdef mara
# MARA CLI zsh completions
# Add to ~/.zshrc or put in $fpath

_mara() {
    local -a commands
    commands=(
        'pins:GPIO pin management'
        'build:Firmware build operations'
        'generate:Code generation'
        'run:Robot runtime connections'
        'record:Record telemetry session'
        'replay:Replay recorded session'
        'config:Configuration management'
        'dashboard:Launch web dashboard'
        'flash:Flash firmware to ESP32'
        'monitor:Live monitoring dashboard'
        'calibrate:Calibration wizards'
        'test:Run robot self-tests'
        'logs:View and manage recorded sessions'
        'sim:Launch simulation mode'
        'version:Show version information'
        'completions:Generate shell completions'
    )

    local -a pins_commands
    pins_commands=(
        'pinout:Visual board diagram'
        'list:Show all pins'
        'free:Show available pins'
        'info:Pin details'
        'assign:Assign a pin'
        'remove:Remove assignment'
        'suggest:Suggest pins for use case'
        'validate:Validate assignments'
        'interactive:Interactive mode'
        'conflicts:Check for conflicts'
        'wizard:Guided setup'
        'clear:Clear all assignments'
    )

    local -a build_commands
    build_commands=(
        'compile:Compile firmware'
        'upload:Flash to ESP32'
        'clean:Clean build artifacts'
        'test:Run firmware tests'
        'features:List available features'
        'size:Show firmware size'
        'watch:Watch and rebuild'
    )

    local -a generate_commands
    generate_commands=(
        'all:Run all generators'
        'commands:Generate command defs'
        'pins:Generate pin config'
        'can:Generate CAN defs'
        'telemetry:Generate telemetry'
        'binary:Generate binary commands'
        'gpio:Generate GPIO mappings'
    )

    local -a run_commands
    run_commands=(
        'serial:Connect via serial'
        'tcp:Connect via TCP/WiFi'
        'can:Connect via CAN bus'
        'mqtt:Connect via MQTT'
        'shell:Interactive command shell'
    )

    _arguments -C \\
        '-h[Show help]' \\
        '--help[Show help]' \\
        '-v[Verbose output]' \\
        '--verbose[Verbose output]' \\
        '1: :->command' \\
        '*:: :->args'

    case $state in
        command)
            _describe -t commands 'mara commands' commands
            ;;
        args)
            case $words[1] in
                pins)
                    _describe -t pins_commands 'pin commands' pins_commands
                    ;;
                build)
                    _describe -t build_commands 'build commands' build_commands
                    ;;
                generate)
                    _describe -t generate_commands 'generators' generate_commands
                    ;;
                run)
                    _describe -t run_commands 'transports' run_commands
                    ;;
            esac
            ;;
    esac
}

_mara "$@"
'''


def _generate_fish() -> str:
    """Generate fish completions."""
    return '''# MARA CLI fish completions
# Save to ~/.config/fish/completions/mara.fish

# Disable file completions
complete -c mara -f

# Top-level commands
complete -c mara -n __fish_use_subcommand -a pins -d 'GPIO pin management'
complete -c mara -n __fish_use_subcommand -a build -d 'Firmware build operations'
complete -c mara -n __fish_use_subcommand -a generate -d 'Code generation'
complete -c mara -n __fish_use_subcommand -a run -d 'Robot runtime connections'
complete -c mara -n __fish_use_subcommand -a record -d 'Record telemetry session'
complete -c mara -n __fish_use_subcommand -a replay -d 'Replay recorded session'
complete -c mara -n __fish_use_subcommand -a config -d 'Configuration management'
complete -c mara -n __fish_use_subcommand -a dashboard -d 'Launch web dashboard'
complete -c mara -n __fish_use_subcommand -a flash -d 'Flash firmware to ESP32'
complete -c mara -n __fish_use_subcommand -a monitor -d 'Live monitoring dashboard'
complete -c mara -n __fish_use_subcommand -a calibrate -d 'Calibration wizards'
complete -c mara -n __fish_use_subcommand -a test -d 'Run robot self-tests'
complete -c mara -n __fish_use_subcommand -a logs -d 'View recorded sessions'
complete -c mara -n __fish_use_subcommand -a sim -d 'Launch simulation mode'
complete -c mara -n __fish_use_subcommand -a version -d 'Show version information'
complete -c mara -n __fish_use_subcommand -a completions -d 'Generate shell completions'

# pins subcommands
complete -c mara -n '__fish_seen_subcommand_from pins' -a pinout -d 'Visual board diagram'
complete -c mara -n '__fish_seen_subcommand_from pins' -a list -d 'Show all pins'
complete -c mara -n '__fish_seen_subcommand_from pins' -a free -d 'Show available pins'
complete -c mara -n '__fish_seen_subcommand_from pins' -a info -d 'Pin details'
complete -c mara -n '__fish_seen_subcommand_from pins' -a assign -d 'Assign a pin'
complete -c mara -n '__fish_seen_subcommand_from pins' -a remove -d 'Remove assignment'
complete -c mara -n '__fish_seen_subcommand_from pins' -a suggest -d 'Suggest pins'
complete -c mara -n '__fish_seen_subcommand_from pins' -a validate -d 'Validate assignments'
complete -c mara -n '__fish_seen_subcommand_from pins' -a interactive -d 'Interactive mode'
complete -c mara -n '__fish_seen_subcommand_from pins' -a conflicts -d 'Check conflicts'
complete -c mara -n '__fish_seen_subcommand_from pins' -a wizard -d 'Guided setup'
complete -c mara -n '__fish_seen_subcommand_from pins' -a clear -d 'Clear all'

# build subcommands
complete -c mara -n '__fish_seen_subcommand_from build' -a compile -d 'Compile firmware'
complete -c mara -n '__fish_seen_subcommand_from build' -a upload -d 'Flash to ESP32'
complete -c mara -n '__fish_seen_subcommand_from build' -a clean -d 'Clean build'
complete -c mara -n '__fish_seen_subcommand_from build' -a test -d 'Run tests'
complete -c mara -n '__fish_seen_subcommand_from build' -a features -d 'List features'
complete -c mara -n '__fish_seen_subcommand_from build' -a size -d 'Show size'
complete -c mara -n '__fish_seen_subcommand_from build' -a watch -d 'Watch and rebuild'

# generate subcommands
complete -c mara -n '__fish_seen_subcommand_from generate' -a all -d 'Run all generators'
complete -c mara -n '__fish_seen_subcommand_from generate' -a commands -d 'Command defs'
complete -c mara -n '__fish_seen_subcommand_from generate' -a pins -d 'Pin config'
complete -c mara -n '__fish_seen_subcommand_from generate' -a can -d 'CAN defs'
complete -c mara -n '__fish_seen_subcommand_from generate' -a telemetry -d 'Telemetry'
complete -c mara -n '__fish_seen_subcommand_from generate' -a binary -d 'Binary commands'
complete -c mara -n '__fish_seen_subcommand_from generate' -a gpio -d 'GPIO mappings'

# run subcommands
complete -c mara -n '__fish_seen_subcommand_from run' -a serial -d 'Serial port'
complete -c mara -n '__fish_seen_subcommand_from run' -a tcp -d 'TCP/WiFi'
complete -c mara -n '__fish_seen_subcommand_from run' -a can -d 'CAN bus'
complete -c mara -n '__fish_seen_subcommand_from run' -a mqtt -d 'MQTT broker'
complete -c mara -n '__fish_seen_subcommand_from run' -a shell -d 'Interactive shell'

# Global flags
complete -c mara -s h -l help -d 'Show help'
complete -c mara -s v -l verbose -d 'Verbose output'
'''


def _install_completions(shell: str, script: str) -> int:
    """Install completions to appropriate location."""
    import os

    home = Path.home()

    if shell == "bash":
        # Try different locations
        locations = [
            home / ".bash_completion.d" / "mara",
            home / ".local" / "share" / "bash-completion" / "completions" / "mara",
        ]
        for loc in locations:
            try:
                loc.parent.mkdir(parents=True, exist_ok=True)
                loc.write_text(script)
                print_success(f"Installed bash completions to {loc}")
                print_info("Restart your shell or run: source ~/.bashrc")
                return 0
            except PermissionError:
                continue

        # Fallback: append to .bashrc
        bashrc = home / ".bashrc"
        print_warning("Could not write to completion directory")
        print_info(f"Add the following to {bashrc}:")
        console.print()
        console.print("[dim]# MARA CLI completions[/dim]")
        console.print("[dim]source /path/to/mara-completions.bash[/dim]")
        return 0

    elif shell == "zsh":
        fpath_dir = home / ".zsh" / "completions"
        fpath_dir.mkdir(parents=True, exist_ok=True)
        comp_file = fpath_dir / "_mara"
        comp_file.write_text(script)
        print_success(f"Installed zsh completions to {comp_file}")
        print_info("Add to ~/.zshrc: fpath=(~/.zsh/completions $fpath)")
        print_info("Then run: autoload -Uz compinit && compinit")
        return 0

    elif shell == "fish":
        fish_dir = home / ".config" / "fish" / "completions"
        fish_dir.mkdir(parents=True, exist_ok=True)
        comp_file = fish_dir / "mara.fish"
        comp_file.write_text(script)
        print_success(f"Installed fish completions to {comp_file}")
        print_info("Completions will be available in new fish sessions")
        return 0

    return 1
