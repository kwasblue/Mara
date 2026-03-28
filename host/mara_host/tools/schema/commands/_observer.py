# schema/commands/_observer.py
"""Observer command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


OBSERVER_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_OBSERVER_CONFIG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Configure a Luenberger state observer.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3, description="Observer slot index (0-3)."),
            "num_states": FieldDef(type="int", required=True, minimum=1, maximum=6, description="Number of states to estimate."),
            "num_inputs": FieldDef(type="int", default=1, minimum=1, maximum=2, description="Number of control inputs (u)."),
            "num_outputs": FieldDef(type="int", required=True, minimum=1, maximum=4, description="Number of measurements (y)."),
            "rate_hz": FieldDef(type="int", default=200, minimum=50, maximum=1000, description="Observer update rate in Hz."),
            "input_ids": FieldDef(type="array", required=True, items=FieldDef(type="int"), description="Signal IDs for control inputs (u)."),
            "output_ids": FieldDef(type="array", required=True, items=FieldDef(type="int"), description="Signal IDs for measurements (y)."),
            "estimate_ids": FieldDef(type="array", required=True, items=FieldDef(type="int"), description="Signal IDs where state estimates (x̂) are written."),
        },
    ),
    "CMD_OBSERVER_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable a configured observer.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3),
            "enable": FieldDef(type="bool", required=True),
        },
    ),
    "CMD_OBSERVER_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset observer state estimate to zero.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3),
        },
    ),
    "CMD_OBSERVER_SET_PARAM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set individual matrix element (e.g., 'A01', 'L10').",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3),
            "key": FieldDef(type="string", required=True, description="Matrix element: 'Aij', 'Bij', 'Cij', or 'Lij' (i=row, j=col)."),
            "value": FieldDef(type="float", required=True),
        },
    ),
    "CMD_OBSERVER_SET_PARAM_ARRAY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set full matrix (A, B, C, or L) in row-major order.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3),
            "key": FieldDef(type="string", required=True, enum=("A", "B", "C", "L"), description="Matrix name."),
            "values": FieldDef(type="array", required=True, items=FieldDef(type="float"), description="Matrix values in row-major order."),
        },
    ),
    "CMD_OBSERVER_STATUS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get observer status and current state estimates.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=3),
        },
    ),
}

OBSERVER_COMMANDS: dict[str, dict] = export_command_dicts(OBSERVER_COMMAND_OBJECTS)
