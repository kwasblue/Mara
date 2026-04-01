# mara_host/cli/commands/generate.py
"""Code generation commands for MARA CLI.

All generation is routed through CodeGeneratorService so that
MCP, HTTP, and other entry points have access to the same functionality.
"""

import argparse

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
)
from mara_host.services.codegen.generator_service import (
    CodeGeneratorService,
    GeneratorType,
    GeneratorResult,
)


# Singleton service instance
_service: CodeGeneratorService | None = None


def _get_service() -> CodeGeneratorService:
    """Get or create the generator service."""
    global _service
    if _service is None:
        _service = CodeGeneratorService()
    return _service


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

    # build-config (first - others may depend on it)
    bc_p = gen_sub.add_parser(
        "build-config",
        help="Generate build configuration (C++ header + Python module)",
    )
    bc_p.set_defaults(func=cmd_build_config)

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

    # mcp
    mcp_p = gen_sub.add_parser(
        "mcp",
        help="Generate MCP/HTTP server tools",
    )
    mcp_p.set_defaults(func=cmd_mcp)

    # control-graph
    cg_p = gen_sub.add_parser(
        "control-graph",
        help="Generate control-graph type registry",
    )
    cg_p.set_defaults(func=cmd_control_graph)

    # tooling
    tooling_p = gen_sub.add_parser(
        "tooling",
        help="Generate tooling backend loaders",
    )
    tooling_p.set_defaults(func=cmd_tooling)

    # hardware
    hw_p = gen_sub.add_parser(
        "hardware",
        help="Generate hardware stubs (sensors, actuators, transports)",
    )
    hw_p.set_defaults(func=cmd_hardware)

    # Default handler
    gen_parser.set_defaults(func=cmd_all)


def _run_generator_with_output(gen_type: GeneratorType) -> GeneratorResult:
    """Run a generator with colored output."""
    name = gen_type.value.replace("_", " ").title()
    console.print(f"[cyan]► {name}[/cyan]")

    service = _get_service()
    result = service.generate(gen_type)

    if result.success:
        console.print(f"  [green]✓[/green] {name} [dim]done[/dim]")
    else:
        console.print(f"  [red]✗[/red] {name} [red]failed[/red]")
        if result.error:
            console.print(f"    [red]{result.error}[/red]")

    console.print()
    return result


def cmd_all(args: argparse.Namespace) -> int:
    """Run all code generators."""
    console.print()
    console.print("[bold cyan]Running all code generators[/bold cyan]")
    console.print()

    # Run generators in order with colored output
    generators = [
        GeneratorType.BUILD_CONFIG,
        GeneratorType.VERSION,
        GeneratorType.COMMANDS,
        GeneratorType.PINS,
        GeneratorType.GPIO,
        GeneratorType.BINARY,
        GeneratorType.TELEMETRY,
        GeneratorType.CAN,
        GeneratorType.MCP,
        GeneratorType.CONTROL_GRAPH,
        GeneratorType.TOOLING,
        GeneratorType.HARDWARE,
    ]

    results = []
    for gen_type in generators:
        result = _run_generator_with_output(gen_type)
        results.append(result)

    failed = sum(1 for r in results if not r.success)
    if failed == 0:
        print_success("All generators completed successfully")
        return 0
    else:
        print_error(f"{failed} generator(s) failed")
        return 1


def _run_single(gen_type: GeneratorType, title: str, files_info: str) -> int:
    """Run a single generator and print results."""
    console.print()
    console.print(f"[bold cyan]{title}[/bold cyan]")
    console.print()

    service = _get_service()
    result = service.generate(gen_type)

    _print_result(result)
    console.print()

    if result.success:
        print_success(f"{title.split()[-1]} generated")
        if files_info:
            print_info(f"Generated: {files_info}")
        return 0
    return 1


def cmd_build_config(args: argparse.Namespace) -> int:
    """Generate build configuration from mara_build.yaml."""
    return _run_single(
        GeneratorType.BUILD_CONFIG,
        "Generating build configuration",
        "GeneratedBuildConfig.h, _generated_config.py",
    )


def cmd_commands(args: argparse.Namespace) -> int:
    """Generate command definitions."""
    return _run_single(
        GeneratorType.COMMANDS,
        "Generating command definitions",
        "CommandDefs.h, command_defs.py, client_commands.py, commands.json",
    )


def cmd_pins(args: argparse.Namespace) -> int:
    """Generate pin configuration."""
    return _run_single(
        GeneratorType.PINS,
        "Generating pin configuration",
        "PinConfig.h, pin_config.py",
    )


def cmd_can(args: argparse.Namespace) -> int:
    """Generate CAN bus definitions."""
    return _run_single(
        GeneratorType.CAN,
        "Generating CAN bus definitions",
        "CanDefs.h, can_defs_generated.py",
    )


def cmd_telemetry(args: argparse.Namespace) -> int:
    """Generate telemetry sections."""
    return _run_single(
        GeneratorType.TELEMETRY,
        "Generating telemetry sections",
        "TelemetrySections.h, telemetry_sections.py",
    )


def cmd_binary(args: argparse.Namespace) -> int:
    """Generate binary command definitions."""
    return _run_single(
        GeneratorType.BINARY,
        "Generating binary command definitions",
        "BinaryCommands.h, binary_commands.py, json_to_binary.py",
    )


def cmd_gpio(args: argparse.Namespace) -> int:
    """Generate GPIO channel mappings."""
    return _run_single(
        GeneratorType.GPIO,
        "Generating GPIO channel mappings",
        "GpioChannelDefs.h, gpio_channels.py",
    )


def cmd_mcp(args: argparse.Namespace) -> int:
    """Generate MCP/HTTP server tools."""
    return _run_single(
        GeneratorType.MCP,
        "Generating MCP/HTTP server tools",
        "_generated_tools.py, _generated_http.py",
    )


def cmd_control_graph(args: argparse.Namespace) -> int:
    """Generate control-graph type registry."""
    return _run_single(
        GeneratorType.CONTROL_GRAPH,
        "Generating control-graph registry",
        "control_graph_registry.json, control_graph_defs.py, control_graph_schema.json",
    )


def cmd_tooling(args: argparse.Namespace) -> int:
    """Generate tooling backend loaders."""
    return _run_single(
        GeneratorType.TOOLING,
        "Generating tooling backend loaders",
        "_generated_loaders.py",
    )


def cmd_hardware(args: argparse.Namespace) -> int:
    """Generate hardware stubs from typed schema definitions."""
    return _run_single(
        GeneratorType.HARDWARE,
        "Generating hardware stubs",
        "firmware stubs (sensor/actuator/transport) and Python API classes",
    )
