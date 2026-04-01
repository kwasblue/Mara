# schema/hardware/transports/_uart.py
"""UART transport definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import TransportDef, FirmwareHints, PythonHints

TRANSPORT = TransportDef(
    name="uart",
    layer="physical",
    description="UART serial communication interface",
    commands={
        "CMD_UART_CONFIG": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Configure UART parameters.",
            payload={
                "uart_id": CmdFieldDef(type="int", default=0),
                "baud_rate": CmdFieldDef(type="int", default=115200),
                "data_bits": CmdFieldDef(type="int", default=8, enum=(7, 8)),
                "stop_bits": CmdFieldDef(type="int", default=1, enum=(1, 2)),
                "parity": CmdFieldDef(
                    type="string",
                    default="none",
                    enum=("none", "even", "odd"),
                ),
            },
        ),
    },
    firmware=FirmwareHints(
        class_name="UartTransport",
        feature_flag="HAS_UART",
        capability="CAP_UART",
    ),
    python=PythonHints(
        api_class="UartTransport",
        reading_class="UartConfig",
        telemetry_topic="transport.uart",
    ),
)
