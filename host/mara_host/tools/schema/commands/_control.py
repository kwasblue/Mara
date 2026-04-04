# schema/commands/_control.py
"""Control kernel command definitions (signal bus + slots)."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


CONTROL_COMMAND_OBJECTS: dict[str, CommandDef] = {
    # Signal Bus
    "CMD_CTRL_SIGNAL_DEFINE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Define a new signal in the signal bus. Only allowed when IDLE.",
        payload={
            "id": FieldDef(type="int", required=True, description="Unique signal ID."),
            "name": FieldDef(type="string", required=True, description="Human-readable signal name."),
            "signal_kind": FieldDef(
                type="string",
                required=True,
                enum=("REF", "MEAS", "OUT", "EST"),
                description="Signal kind: REF = reference/setpoint, MEAS = measurement/feedback, OUT = control output, EST = state estimate.",
            ),
            "initial": FieldDef(type="float", default=0.0, description="Initial value."),
        },
    ),
    "CMD_CTRL_SIGNALS_CLEAR": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Clear all signals from the signal bus.",
    ),
    "CMD_CTRL_SIGNAL_SET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set a signal value in the signal bus.",
        payload={
            "id": FieldDef(type="int", required=True, description="Signal ID."),
            "value": FieldDef(type="float", required=True, description="Value to set."),
        },
    ),
    "CMD_CTRL_SIGNAL_GET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get a signal value from the signal bus.",
        payload={
            "id": FieldDef(type="int", required=True, description="Signal ID."),
        },
    ),
    "CMD_CTRL_SIGNALS_LIST": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="List all defined signals in the signal bus.",
    ),
    "CMD_CTRL_SIGNAL_DELETE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Delete a signal from the signal bus.",
        payload={
            "id": FieldDef(type="integer", description="Signal ID to delete"),
        },
    ),
    "CMD_CTRL_SIGNAL_TRACE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Subscribe to trace specific signals via telemetry at a configurable rate.",
        payload={
            "signal_ids": FieldDef(
                type="array",
                items=FieldDef(type="int"),
                description="List of signal IDs to trace (max 16). Empty array disables tracing.",
            ),
            "rate_hz": FieldDef(
                type="int",
                default=10,
                minimum=1,
                maximum=50,
                description="Update rate in Hz (1-50, default 10).",
            ),
        },
    ),
    "CMD_CTRL_AUTO_SIGNALS_CONFIG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Configure auto-signal publishing from hardware managers (IMU, encoders, etc). Requires ARMED state.",
        payload={
            "imu": FieldDef(
                type="object",
                description="IMU auto-signal config: {enabled: bool, rate_hz: int}",
            ),
            "encoder": FieldDef(
                type="object",
                description="Encoder auto-signal config: {enabled: bool, rate_hz: int}",
            ),
        },
    ),

    # Slot Configuration
    "CMD_CTRL_SLOT_CONFIG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Configure a control slot with controller type and signal routing. Only allowed when IDLE.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
            "controller_type": FieldDef(
                type="string",
                required=True,
                enum=("PID", "STATE_SPACE", "SS"),
                description="Controller type: PID or STATE_SPACE.",
            ),
            "rate_hz": FieldDef(type="int", default=100, minimum=1, maximum=1000, description="Controller update rate in Hz."),
            "ref_id": FieldDef(type="int", description="Signal ID for reference/setpoint (PID mode)."),
            "meas_id": FieldDef(type="int", description="Signal ID for measurement/feedback (PID mode)."),
            "out_id": FieldDef(type="int", description="Signal ID for control output (PID mode)."),
            "num_states": FieldDef(type="int", default=2, minimum=1, maximum=6, description="Number of state variables (STATE_SPACE mode)."),
            "num_inputs": FieldDef(type="int", default=1, minimum=1, maximum=2, description="Number of control inputs (STATE_SPACE mode)."),
            "state_ids": FieldDef(type="array", items=FieldDef(type="int"), description="Signal IDs for state measurements (STATE_SPACE mode)."),
            "ref_ids": FieldDef(type="array", items=FieldDef(type="int"), description="Signal IDs for state references (STATE_SPACE mode)."),
            "output_ids": FieldDef(type="array", items=FieldDef(type="int"), description="Signal IDs for control outputs (STATE_SPACE mode)."),
            "require_armed": FieldDef(type="bool", default=True, description="Only run when robot is armed."),
            "require_active": FieldDef(type="bool", default=True, description="Only run when robot is active."),
        },
    ),
    "CMD_CTRL_SLOT_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable a configured control slot.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
            "enable": FieldDef(type="bool", required=True, description="True to enable, False to disable."),
        },
    ),
    "CMD_CTRL_SLOT_GET_PARAM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get a scalar parameter from a control slot's controller.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
            "key": FieldDef(type="string", required=True, description="Parameter name (e.g., 'kp', 'ki', 'kd' for PID; 'k00', 'ki0' for STATE_SPACE)."),
        },
    ),
    "CMD_CTRL_SLOT_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset a control slot's internal state (integrators, etc).",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
        },
    ),
    "CMD_CTRL_SLOT_SET_PARAM": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set a scalar parameter on a control slot's controller.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
            "key": FieldDef(type="string", required=True, description="Parameter name (e.g., 'kp', 'ki', 'kd', 'out_min', 'out_max' for PID; 'k00', 'ki0', 'u0_min' for STATE_SPACE)."),
            "value": FieldDef(type="float", required=True, description="Parameter value."),
        },
    ),
    "CMD_CTRL_SLOT_SET_PARAM_ARRAY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Set an array parameter on a control slot (e.g., gain matrix K for state-space).",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
            "key": FieldDef(type="string", required=True, description="Parameter name ('K' = state feedback, 'Kr' = reference feedforward, 'Ki' = integral gains)."),
            "values": FieldDef(type="array", required=True, items={"type": "float"}, description="Array of float values. For K/Kr: row-major order [k00,k01,...,k10,k11,...]. For Ki: one per output."),
        },
    ),
    "CMD_CTRL_SLOT_STATUS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get status of a control slot.",
        payload={
            "slot": FieldDef(type="int", required=True, minimum=0, maximum=7, description="Slot index (0-7)."),
        },
    ),

    # Runtime control-graph upload/status surface
    "CMD_CTRL_GRAPH_UPLOAD": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Upload a runtime control-graph config. Use commit=false for two-phase commit (requires CMD_CTRL_GRAPH_COMMIT to activate).",
        payload={
            "graph": FieldDef(type="object", required=True, description="Normalized control-graph config with schema_version and slots."),
            "commit": FieldDef(type="bool", default=True, description="If true (default), immediately activate. If false, stage as pending and return token for later commit."),
            "mode": FieldDef(
                type="string",
                default="replace",
                enum=("replace", "merge"),
                description="Upload mode: 'replace' clears all and uploads new (default), 'merge' preserves runtime state for unchanged slots.",
            ),
        },
    ),
    "CMD_CTRL_GRAPH_CLEAR": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Clear the stored runtime control-graph config.",
    ),
    "CMD_CTRL_GRAPH_ENABLE": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable or disable all stored control-graph slots.",
        payload={
            "enable": FieldDef(type="bool", required=True, description="True to enable all slots, false to disable all slots."),
        },
    ),
    "CMD_CTRL_GRAPH_STATUS": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Get status of the stored runtime control graph.",
    ),
    "CMD_CTRL_GRAPH_DEBUG": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Enable debug streaming for a single slot to see intermediate transform values. Only one slot can be in debug mode at a time.",
        payload={
            "slot_id": FieldDef(
                type="string",
                required=True,
                description="Slot ID to enable debug for, or empty string to disable debug mode.",
            ),
        },
    ),
    "CMD_CTRL_GRAPH_COMMIT": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Commit a pending control graph upload. Use with CMD_CTRL_GRAPH_UPLOAD commit=false for two-phase commit.",
        payload={
            "token": FieldDef(
                type="int",
                required=True,
                description="Token returned from the pending upload to confirm.",
            ),
        },
    ),
    "CMD_MCU_DIAGNOSTICS_QUERY": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Query persisted MCU diagnostics and mirrored persistence metadata.",
    ),
    "CMD_MCU_DIAGNOSTICS_RESET": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Reset persisted MCU diagnostics counters while preserving boot identity fields.",
    ),
}

CONTROL_COMMANDS: dict[str, dict] = export_command_dicts(CONTROL_COMMAND_OBJECTS)
