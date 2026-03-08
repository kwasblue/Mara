# mara_host/cli/commands/diagram.py
"""Block diagram CLI commands for MARA."""

import argparse
import json
from pathlib import Path

from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table

from mara_host.cli.console import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
)


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register diagram commands."""
    parser = subparsers.add_parser(
        "diagram",
        help="Block diagram operations",
        description="Create, inspect, and manage block diagrams",
    )

    sub = parser.add_subparsers(
        dest="diagram_cmd",
        title="diagram commands",
        metavar="<subcommand>",
    )

    # info - show diagram file info
    info_p = sub.add_parser(
        "info",
        help="Show information about a diagram file",
    )
    info_p.add_argument(
        "file",
        type=Path,
        help="Path to diagram JSON file",
    )
    info_p.set_defaults(func=cmd_info)

    # list - list blocks and connections
    list_p = sub.add_parser(
        "list",
        help="List blocks and connections in a diagram",
    )
    list_p.add_argument(
        "file",
        type=Path,
        help="Path to diagram JSON file",
    )
    list_p.add_argument(
        "--blocks",
        action="store_true",
        help="List only blocks",
    )
    list_p.add_argument(
        "--connections",
        action="store_true",
        help="List only connections",
    )
    list_p.set_defaults(func=cmd_list)

    # create - create a new diagram template
    create_p = sub.add_parser(
        "create",
        help="Create a new diagram template",
    )
    create_p.add_argument(
        "output",
        type=Path,
        help="Output file path",
    )
    create_p.add_argument(
        "--type",
        choices=["hardware", "control"],
        default="hardware",
        help="Diagram type (default: hardware)",
    )
    create_p.add_argument(
        "--template",
        choices=["empty", "basic-pid", "motor-pair"],
        default="empty",
        help="Template to use (default: empty)",
    )
    create_p.set_defaults(func=cmd_create)

    # validate - validate diagram structure
    validate_p = sub.add_parser(
        "validate",
        help="Validate diagram file structure",
    )
    validate_p.add_argument(
        "file",
        type=Path,
        help="Path to diagram JSON file",
    )
    validate_p.set_defaults(func=cmd_validate)

    # export-config - export PID/observer config to commands
    export_p = sub.add_parser(
        "export-config",
        help="Export controller configuration as commands",
    )
    export_p.add_argument(
        "file",
        type=Path,
        help="Path to control loop diagram JSON",
    )
    export_p.add_argument(
        "--format",
        choices=["shell", "python", "json"],
        default="shell",
        help="Output format (default: shell)",
    )
    export_p.set_defaults(func=cmd_export_config)


def cmd_info(args: argparse.Namespace) -> int:
    """Show diagram file information."""
    path = args.file

    if not path.exists():
        print_error(f"File not found: {path}")
        return 1

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        return 1

    diagram_type = data.get("diagram_type", "unknown")
    name = data.get("name", "Untitled")
    blocks = data.get("blocks", [])
    connections = data.get("connections", [])

    # Build info tree
    tree = Tree(f"[bold]{path.name}[/bold]")
    tree.add(f"Name: {name}")
    tree.add(f"Type: {diagram_type}")
    tree.add(f"Blocks: {len(blocks)}")
    tree.add(f"Connections: {len(connections)}")

    if blocks:
        blocks_node = tree.add("Block Types:")
        type_counts: dict[str, int] = {}
        for block in blocks:
            bt = block.get("block_type", "unknown")
            type_counts[bt] = type_counts.get(bt, 0) + 1
        for bt, count in sorted(type_counts.items()):
            blocks_node.add(f"{bt}: {count}")

    console.print(Panel(tree, title="Diagram Info"))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List blocks and connections in a diagram."""
    path = args.file

    if not path.exists():
        print_error(f"File not found: {path}")
        return 1

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        return 1

    blocks = data.get("blocks", [])
    connections = data.get("connections", [])

    show_all = not args.blocks and not args.connections

    # Blocks table
    if show_all or args.blocks:
        table = Table(title="Blocks", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Label")
        table.add_column("Position")

        for block in blocks:
            table.add_row(
                block.get("block_id", "?"),
                block.get("block_type", "?"),
                block.get("label", ""),
                f"({block.get('x', 0):.0f}, {block.get('y', 0):.0f})",
            )

        console.print(table)
        console.print()

    # Connections table
    if show_all or args.connections:
        table = Table(title="Connections", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("From", style="green")
        table.add_column("To", style="yellow")
        table.add_column("Signal")

        for conn in connections:
            from_str = f"{conn.get('from_block', '?')}.{conn.get('from_port', '?')}"
            to_str = f"{conn.get('to_block', '?')}.{conn.get('to_port', '?')}"
            signal_id = conn.get("signal_id")
            signal_str = f"S{signal_id}" if signal_id is not None else "-"

            table.add_row(
                conn.get("connection_id", "?"),
                from_str,
                to_str,
                signal_str,
            )

        console.print(table)

    return 0


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new diagram template."""
    output = args.output
    diagram_type = args.type
    template = args.template

    if output.exists():
        print_warning(f"File already exists: {output}")
        response = console.input("Overwrite? [y/N] ")
        if response.lower() != "y":
            return 1

    # Build diagram data
    data = {
        "diagram_type": diagram_type,
        "name": output.stem,
        "blocks": [],
        "connections": [],
        "metadata": {
            "template": template,
        },
    }

    if template == "basic-pid" and diagram_type == "control":
        # Create basic PID loop template
        data["blocks"] = [
            {
                "block_type": "signal_source",
                "block_id": "ref_0",
                "label": "Ref",
                "x": 50,
                "y": 150,
                "width": 70,
                "height": 50,
                "properties": {"signal_id": 0, "kind": "reference"},
            },
            {
                "block_type": "pid",
                "block_id": "pid_0",
                "label": "PID",
                "x": 200,
                "y": 140,
                "width": 100,
                "height": 80,
                "properties": {
                    "slot": 0,
                    "kp": 1.0,
                    "ki": 0.0,
                    "kd": 0.0,
                },
            },
            {
                "block_type": "signal_sink",
                "block_id": "out_0",
                "label": "Out",
                "x": 400,
                "y": 155,
                "width": 70,
                "height": 50,
                "properties": {"signal_id": 1},
            },
        ]
        data["connections"] = [
            {
                "connection_id": "conn_0",
                "from_block": "ref_0",
                "from_port": "out",
                "to_block": "pid_0",
                "to_port": "ref",
            },
            {
                "connection_id": "conn_1",
                "from_block": "pid_0",
                "from_port": "out",
                "to_block": "out_0",
                "to_port": "in",
            },
        ]

    elif template == "motor-pair" and diagram_type == "hardware":
        # Create motor pair template
        data["blocks"] = [
            {
                "block_type": "esp32",
                "block_id": "esp32_0",
                "label": "ESP32",
                "x": 200,
                "y": 50,
                "width": 160,
                "height": 320,
                "properties": {"variant": "DevKitC"},
            },
            {
                "block_type": "motor",
                "block_id": "motor_0",
                "label": "Motor L",
                "x": 50,
                "y": 100,
                "width": 100,
                "height": 80,
                "properties": {"motor_id": 0},
            },
            {
                "block_type": "motor",
                "block_id": "motor_1",
                "label": "Motor R",
                "x": 50,
                "y": 220,
                "width": 100,
                "height": 80,
                "properties": {"motor_id": 1},
            },
        ]

    # Write file
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(data, f, indent=2)

    print_success(f"Created {diagram_type} diagram: {output}")
    print_info(f"Template: {template}")
    print_info(f"Blocks: {len(data['blocks'])}, Connections: {len(data['connections'])}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate diagram file structure."""
    path = args.file

    if not path.exists():
        print_error(f"File not found: {path}")
        return 1

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        return 1

    errors = []
    warnings = []

    # Check required fields
    if "diagram_type" not in data:
        errors.append("Missing 'diagram_type' field")

    if "blocks" not in data:
        errors.append("Missing 'blocks' array")
    elif not isinstance(data["blocks"], list):
        errors.append("'blocks' must be an array")

    if "connections" not in data:
        warnings.append("Missing 'connections' array")
    elif not isinstance(data["connections"], list):
        errors.append("'connections' must be an array")

    # Validate blocks
    block_ids = set()
    for i, block in enumerate(data.get("blocks", [])):
        if not isinstance(block, dict):
            errors.append(f"Block {i} is not an object")
            continue

        block_id = block.get("block_id")
        if not block_id:
            errors.append(f"Block {i} missing 'block_id'")
        elif block_id in block_ids:
            errors.append(f"Duplicate block_id: {block_id}")
        else:
            block_ids.add(block_id)

        if not block.get("block_type"):
            errors.append(f"Block {block_id or i} missing 'block_type'")

    # Validate connections
    for i, conn in enumerate(data.get("connections", [])):
        if not isinstance(conn, dict):
            errors.append(f"Connection {i} is not an object")
            continue

        from_block = conn.get("from_block")
        to_block = conn.get("to_block")

        if from_block and from_block not in block_ids:
            errors.append(f"Connection {i} references unknown block: {from_block}")

        if to_block and to_block not in block_ids:
            errors.append(f"Connection {i} references unknown block: {to_block}")

    # Report results
    if errors:
        print_error(f"Validation failed with {len(errors)} error(s):")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
    else:
        print_success("Diagram is valid")

    if warnings:
        for warn in warnings:
            print_warning(warn)

    return 1 if errors else 0


def cmd_export_config(args: argparse.Namespace) -> int:
    """Export controller configuration as commands."""
    path = args.file
    fmt = args.format

    if not path.exists():
        print_error(f"File not found: {path}")
        return 1

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        return 1

    blocks = data.get("blocks", [])

    # Find PID and observer blocks
    pid_blocks = [b for b in blocks if b.get("block_type") == "pid"]
    observer_blocks = [b for b in blocks if b.get("block_type") == "observer"]

    if not pid_blocks and not observer_blocks:
        print_warning("No PID or observer blocks found in diagram")
        return 0

    if fmt == "json":
        # Output as JSON
        output = {
            "controllers": [
                {
                    "slot": b["properties"].get("slot", 0),
                    "kp": b["properties"].get("kp", 1.0),
                    "ki": b["properties"].get("ki", 0.0),
                    "kd": b["properties"].get("kd", 0.0),
                    "output_min": b["properties"].get("output_min", -1.0),
                    "output_max": b["properties"].get("output_max", 1.0),
                }
                for b in pid_blocks
            ],
            "observers": [
                {
                    "slot": b["properties"].get("slot", 0),
                    "n_states": b["properties"].get("n_states", 2),
                    "L": b["properties"].get("L", []),
                }
                for b in observer_blocks
            ],
        }
        console.print(Syntax(json.dumps(output, indent=2), "json"))

    elif fmt == "python":
        # Output as Python code
        lines = ["# Auto-generated controller configuration", ""]

        for b in pid_blocks:
            props = b.get("properties", {})
            slot = props.get("slot", 0)
            lines.append(f"# PID Controller Slot {slot}")
            lines.append(f"controller.controller_config({slot}, {{")
            lines.append(f"    'kp': {props.get('kp', 1.0)},")
            lines.append(f"    'ki': {props.get('ki', 0.0)},")
            lines.append(f"    'kd': {props.get('kd', 0.0)},")
            lines.append(f"    'output_min': {props.get('output_min', -1.0)},")
            lines.append(f"    'output_max': {props.get('output_max', 1.0)},")
            lines.append("})")
            lines.append("")

        console.print(Syntax("\n".join(lines), "python"))

    else:
        # Output as shell commands (mara CLI)
        lines = ["# Auto-generated controller commands", ""]

        for b in pid_blocks:
            props = b.get("properties", {})
            slot = props.get("slot", 0)
            kp = props.get("kp", 1.0)
            ki = props.get("ki", 0.0)
            kd = props.get("kd", 0.0)
            lines.append(f"# PID Slot {slot}: {b.get('label', 'PID')}")
            lines.append(
                f"mara send CMD_CTRL_SLOT_CONFIG "
                f"slot={slot} kp={kp} ki={ki} kd={kd}"
            )
            lines.append("")

        console.print(Syntax("\n".join(lines), "bash"))

    return 0
