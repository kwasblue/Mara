# schema/hardware/transports/_can.py
"""CAN bus transport definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import TransportDef, FirmwareHints, PythonHints

TRANSPORT = TransportDef(
    name="can",
    layer="physical",
    description="CAN bus communication for multi-node systems",
    commands={
        "CMD_CAN_INIT": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Initialize CAN bus interface.",
            payload={
                "bitrate": CmdFieldDef(
                    type="int",
                    default=500000,
                    description="CAN bus bitrate in bps",
                ),
                "mode": CmdFieldDef(
                    type="string",
                    default="normal",
                    enum=("normal", "loopback", "silent"),
                ),
            },
        ),
        "CMD_CAN_SEND": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Send CAN message.",
            payload={
                "id": CmdFieldDef(
                    type="int",
                    required=True,
                    description="CAN message ID (11 or 29 bit)",
                ),
                "data": CmdFieldDef(
                    type="array",
                    required=True,
                    description="Data bytes (0-8)",
                    items={"type": "int"},
                ),
                "extended": CmdFieldDef(
                    type="bool",
                    default=False,
                    description="Use extended (29-bit) ID",
                ),
            },
        ),
        "CMD_CAN_FILTER": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Configure CAN receive filter.",
            payload={
                "filter_id": CmdFieldDef(type="int", default=0),
                "id": CmdFieldDef(type="int", required=True),
                "mask": CmdFieldDef(type="int", default=0x7FF),
            },
        ),
        "CMD_CAN_STATUS": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Get CAN bus status.",
            response={
                "initialized": CmdFieldDef(type="bool"),
                "bus_off": CmdFieldDef(type="bool"),
                "error_passive": CmdFieldDef(type="bool"),
                "tx_error_count": CmdFieldDef(type="int"),
                "rx_error_count": CmdFieldDef(type="int"),
            },
        ),
    },
    firmware=FirmwareHints(
        class_name="CanTransport",
        feature_flag="HAS_CAN",
        capability="CAP_CAN",
    ),
    python=PythonHints(
        api_class="CanTransport",
        reading_class="CanStatus",
        telemetry_topic="transport.can",
    ),
)
