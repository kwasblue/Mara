# AUTO-GENERATED FILE — DO NOT EDIT BY HAND
# Generated from VERSION in platform_schema.py

PROTOCOL_VERSION = 1
SCHEMA_VERSION = 1
CLIENT_VERSION = "1.0.0"
BOARD = "esp32"
NAME = "robot"

# Capability bitfield (matches MCU Version.h)
class Capabilities:
    BINARY_PROTOCOL = 0x0001
    INTENT_BUFFERING = 0x0002
    STATE_SPACE_CTRL = 0x0004
    OBSERVERS = 0x0008

CAPABILITIES_MASK = (
    Capabilities.BINARY_PROTOCOL |
    Capabilities.INTENT_BUFFERING |
    Capabilities.STATE_SPACE_CTRL |
    Capabilities.OBSERVERS
)
