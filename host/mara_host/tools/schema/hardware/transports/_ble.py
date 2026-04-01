# schema/hardware/transports/_ble.py
"""Bluetooth Low Energy transport definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import TransportDef, FirmwareHints, PythonHints

TRANSPORT = TransportDef(
    name="ble",
    layer="protocol",
    description="Bluetooth Low Energy communication",
    commands={
        "CMD_BLE_ADVERTISE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Start or stop BLE advertising.",
            payload={
                "enable": CmdFieldDef(type="bool", default=True),
                "name": CmdFieldDef(
                    type="string",
                    default="MARA",
                    description="Device name to advertise",
                ),
            },
        ),
        "CMD_BLE_STATUS": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Get BLE connection status.",
            response={
                "advertising": CmdFieldDef(type="bool"),
                "connected": CmdFieldDef(type="bool"),
                "client_count": CmdFieldDef(type="int"),
            },
        ),
    },
    firmware=FirmwareHints(
        class_name="BleTransport",
        feature_flag="HAS_BLE",
        capability="CAP_BLE",
    ),
    python=PythonHints(
        api_class="BleTransport",
        reading_class="BleStatus",
        telemetry_topic="transport.ble",
    ),
)
