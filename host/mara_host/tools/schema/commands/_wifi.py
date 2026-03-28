# schema/commands/_wifi.py
"""WiFi configuration command definitions."""

from __future__ import annotations

from .core import CommandDef, FieldDef, export_command_dicts


WIFI_COMMAND_OBJECTS: dict[str, CommandDef] = {
    "CMD_WIFI_SCAN": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Scan for available WiFi networks.",
        timeout_s=10.0,
        response={
            "networks": FieldDef(
                type="array",
                description="List of discovered networks",
                items={
                    "ssid": FieldDef(type="string"),
                    "rssi": FieldDef(type="int"),
                    "encrypted": FieldDef(type="bool"),
                },
            ),
        },
    ),
    "CMD_WIFI_JOIN": CommandDef(
        kind="cmd",
        direction="host->mcu",
        description="Connect to a WiFi network.",
        payload={
            "ssid": FieldDef(type="string", required=True, description="Network SSID to connect to"),
            "password": FieldDef(type="string", description="Network password (omit for open networks)"),
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
            "connected": FieldDef(type="bool", description="True if connected to a network"),
            "ssid": FieldDef(type="string", description="Current network SSID"),
            "rssi": FieldDef(type="int", description="Signal strength in dBm"),
            "ip": FieldDef(type="string", description="Assigned IP address"),
        },
    ),
}

WIFI_COMMANDS: dict[str, dict] = export_command_dicts(WIFI_COMMAND_OBJECTS)
