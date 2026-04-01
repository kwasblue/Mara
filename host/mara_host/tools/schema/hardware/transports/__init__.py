# schema/hardware/transports/__init__.py
"""
Transport definitions with auto-discovery.

To add a new transport:
    1. Create _mytransport.py with a TRANSPORT export
    2. Run: mara generate all
"""

from ...discovery import DiscoveryConfig, discover_defs
from ..core import TransportDef

_config = DiscoveryConfig(
    export_name="TRANSPORT",
    expected_type=TransportDef,
    key_attr="name",
    unique_attrs=("name",),
    on_import_error="error",
)

TRANSPORTS = discover_defs(__file__, __name__, _config)

__all__ = ["TRANSPORTS"]
