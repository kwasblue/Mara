# schema/hardware/transports/_mqtt.py
"""MQTT transport definition."""

from ...commands.core import CommandDef, FieldDef as CmdFieldDef
from ..core import TransportDef, FirmwareHints, PythonHints

TRANSPORT = TransportDef(
    name="mqtt",
    layer="protocol",
    description="MQTT message broker protocol",
    commands={
        "CMD_MQTT_CONNECT": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Connect to MQTT broker.",
            payload={
                "broker": CmdFieldDef(
                    type="string",
                    required=True,
                    description="Broker hostname or IP",
                ),
                "port": CmdFieldDef(type="int", default=1883),
                "client_id": CmdFieldDef(
                    type="string",
                    description="Client identifier (auto-generated if omitted)",
                ),
                "username": CmdFieldDef(type="string"),
                "password": CmdFieldDef(type="string"),
            },
            timeout_s=10.0,
        ),
        "CMD_MQTT_DISCONNECT": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Disconnect from MQTT broker.",
        ),
        "CMD_MQTT_PUBLISH": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Publish message to MQTT topic.",
            payload={
                "topic": CmdFieldDef(type="string", required=True),
                "payload": CmdFieldDef(type="string", required=True),
                "qos": CmdFieldDef(type="int", default=0, enum=(0, 1, 2)),
                "retain": CmdFieldDef(type="bool", default=False),
            },
        ),
        "CMD_MQTT_SUBSCRIBE": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Subscribe to MQTT topic.",
            payload={
                "topic": CmdFieldDef(type="string", required=True),
                "qos": CmdFieldDef(type="int", default=0, enum=(0, 1, 2)),
            },
        ),
        "CMD_MQTT_STATUS": CommandDef(
            kind="cmd",
            direction="host->mcu",
            description="Get MQTT connection status.",
            response={
                "connected": CmdFieldDef(type="bool"),
                "broker": CmdFieldDef(type="string"),
                "subscriptions": CmdFieldDef(type="int"),
            },
        ),
    },
    firmware=FirmwareHints(
        class_name="MqttTransport",
        feature_flag="HAS_MQTT",
        capability="CAP_MQTT",
    ),
    python=PythonHints(
        api_class="MqttTransport",
        reading_class="MqttStatus",
        telemetry_topic="transport.mqtt",
    ),
)
