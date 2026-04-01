# schema/hardware/transports/_wifi.py
"""WiFi transport definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import TransportDef, FirmwareHints, PythonHints

TRANSPORT = TransportDef(
    name="wifi",
    layer="protocol",
    description="WiFi 802.11 wireless networking",
    commands={
        "CMD_WIFI_SCAN": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Scan for available WiFi networks.",
            timeout_s=10.0,
            response={
                "networks": CmdFieldDef(
                    type="array",
                    description="List of discovered networks",
                    items={
                        "ssid": CmdFieldDef(type="string"),
                        "rssi": CmdFieldDef(type="int"),
                        "encrypted": CmdFieldDef(type="bool"),
                    },
                ),
            },
        ),
        "CMD_WIFI_JOIN": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Connect to a WiFi network.",
            payload={
                "ssid": CmdFieldDef(
                    type="string",
                    required=True,
                    description="Network SSID to connect to",
                ),
                "password": CmdFieldDef(
                    type="string",
                    description="Network password (omit for open networks)",
                ),
            },
            timeout_s=15.0,
        ),
        "CMD_WIFI_DISCONNECT": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Disconnect from current WiFi network.",
            timeout_s=2.0,
        ),
        "CMD_WIFI_STATUS": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Get current WiFi connection status.",
            response={
                "connected": CmdFieldDef(
                    type="bool",
                    description="True if connected to a network",
                ),
                "ssid": CmdFieldDef(type="string", description="Current network SSID"),
                "rssi": CmdFieldDef(type="int", description="Signal strength in dBm"),
                "ip": CmdFieldDef(type="string", description="Assigned IP address"),
            },
        ),
    },
    firmware=FirmwareHints(
        class_name="WifiTransport",
        feature_flag="HAS_WIFI",
        capability="CAP_WIFI",
    ),
    python=PythonHints(
        api_class="WifiTransport",
        reading_class="WifiStatus",
        telemetry_topic="transport.wifi",
    ),
)
