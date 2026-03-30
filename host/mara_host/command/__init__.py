# mara_host/command/__init__.py
"""
Command handling: client, binary commands, command streamer, reliable commander.

Use explicit imports:
    from mara_host.command.client import MaraClient
    from mara_host.command.binary_commands import BinaryStreamer
    from mara_host.command.factory import MaraClientFactory, create_client_from_args, ClientConfig
    from mara_host.command.interfaces import IMaraClient, ITransport
"""
from typing import TYPE_CHECKING

# These imports are for runtime type checking and IDE support
if TYPE_CHECKING:
    from mara_host.command.client import MaraClient, BaseMaraClient
    from mara_host.command.factory import MaraClientFactory, ClientConfig
    from mara_host.command.interfaces import IMaraClient, ITransport
    from mara_host.command.types import (
        IdentityMessage,
        CommandMessage,
        CommandAck,
        TelemetryMessage,
        RawFrame,
        HelloMessage,
        CommandResult,
        CommandResultWithData,
    )


def __getattr__(name: str):
    """Lazy import for public API."""
    import importlib

    _EXPORTS = {
        "MaraClient": "mara_host.command.client",
        "BaseMaraClient": "mara_host.command.client",
        "MaraClientFactory": "mara_host.command.factory",
        "ClientConfig": "mara_host.command.factory",
        "create_client_from_args": "mara_host.command.factory",
        "IMaraClient": "mara_host.command.interfaces",
        "ITransport": "mara_host.command.interfaces",
        # Protocol message types
        "IdentityMessage": "mara_host.command.types",
        "CommandMessage": "mara_host.command.types",
        "CommandAck": "mara_host.command.types",
        "TelemetryMessage": "mara_host.command.types",
        "RawFrame": "mara_host.command.types",
        "HelloMessage": "mara_host.command.types",
        "CommandResult": "mara_host.command.types",
        "CommandResultWithData": "mara_host.command.types",
    }

    if name in _EXPORTS:
        module = importlib.import_module(_EXPORTS[name])
        return getattr(module, name)

    raise AttributeError(f"module 'mara_host.command' has no attribute '{name}'")


__all__ = [
    # Main client classes
    "MaraClient",
    "BaseMaraClient",
    # Factory
    "MaraClientFactory",
    "ClientConfig",
    "create_client_from_args",
    # Interfaces
    "IMaraClient",
    "ITransport",
    # Protocol message types
    "IdentityMessage",
    "CommandMessage",
    "CommandAck",
    "TelemetryMessage",
    "RawFrame",
    "HelloMessage",
    "CommandResult",
    "CommandResultWithData",
]
