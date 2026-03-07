# mara_host/command/__init__.py
"""
Command handling: client, binary commands, command streamer, reliable commander.

Use explicit imports to avoid circular dependencies:
    from mara_host.command.client import MaraClient
    from mara_host.command.binary_commands import BinaryStreamer
    from mara_host.command.factory import MaraClientFactory, create_client_from_args, ClientConfig
    from mara_host.command.interfaces import IMaraClient, ITransport
    etc.

Backward compatibility:
    AsyncRobotClient is deprecated, use MaraClient instead.
    RobotClientFactory is deprecated, use MaraClientFactory instead.
    IRobotClient is deprecated, use IMaraClient instead.
"""
import warnings as _warnings
from typing import TYPE_CHECKING

# These imports are for runtime type checking and IDE support
if TYPE_CHECKING:
    from mara_host.command.client import MaraClient, BaseMaraClient
    from mara_host.command.factory import MaraClientFactory, ClientConfig
    from mara_host.command.interfaces import IMaraClient, ITransport


def __getattr__(name: str):
    """Provide backward compatibility with deprecation warnings."""

    # Map deprecated names to new names
    _DEPRECATIONS = {
        "AsyncRobotClient": ("MaraClient", "mara_host.command.client"),
        "BaseAsyncRobotClient": ("BaseMaraClient", "mara_host.command.client"),
        "RobotClientFactory": ("MaraClientFactory", "mara_host.command.factory"),
        "IRobotClient": ("IMaraClient", "mara_host.command.interfaces"),
    }

    if name in _DEPRECATIONS:
        new_name, module_path = _DEPRECATIONS[name]
        _warnings.warn(
            f"{name} is deprecated, use {new_name} instead. "
            f"Import from {module_path}.",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, new_name)

    # Direct exports (no deprecation warning)
    _EXPORTS = {
        "MaraClient": "mara_host.command.client",
        "BaseMaraClient": "mara_host.command.client",
        "MaraClientFactory": "mara_host.command.factory",
        "ClientConfig": "mara_host.command.factory",
        "create_client_from_args": "mara_host.command.factory",
        "IMaraClient": "mara_host.command.interfaces",
        "ITransport": "mara_host.command.interfaces",
    }

    if name in _EXPORTS:
        import importlib
        module = importlib.import_module(_EXPORTS[name])
        return getattr(module, name)

    raise AttributeError(f"module 'mara_host.command' has no attribute '{name}'")
