# schema/commands/_wifi.py
"""WiFi configuration command definitions."""

WIFI_COMMANDS: dict[str, dict] = {
    "CMD_WIFI_SCAN": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Scan for available WiFi networks.",
        "payload": {},
        "timeout_s": 10.0,  # WiFi scan can take several seconds
        "response": {
            "networks": {
                "type": "array",
                "description": "List of discovered networks",
                "items": {
                    "ssid": {"type": "string"},
                    "rssi": {"type": "int"},
                    "encrypted": {"type": "bool"},
                },
            },
        },
    },

    "CMD_WIFI_JOIN": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Connect to a WiFi network.",
        "payload": {
            "ssid": {
                "type": "string",
                "required": True,
                "description": "Network SSID to connect to",
            },
            "password": {
                "type": "string",
                "required": False,
                "description": "Network password (omit for open networks)",
            },
        },
        "timeout_s": 15.0,  # WiFi connection can take 10+ seconds
    },

    "CMD_WIFI_DISCONNECT": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Disconnect from current WiFi network.",
        "payload": {},
        "timeout_s": 2.0,
    },

    "CMD_WIFI_STATUS": {
        "kind": "cmd",
        "direction": "host->mcu",
        "description": "Get current WiFi connection status.",
        "payload": {},
        "response": {
            "connected": {"type": "bool", "description": "True if connected to a network"},
            "ssid": {"type": "string", "description": "Current network SSID"},
            "rssi": {"type": "int", "description": "Signal strength in dBm"},
            "ip": {"type": "string", "description": "Assigned IP address"},
        },
    },
}
