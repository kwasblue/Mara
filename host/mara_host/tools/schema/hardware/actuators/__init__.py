# schema/hardware/actuators/__init__.py
"""
Actuator definitions with auto-discovery.

To add a new actuator:
    1. Create _myactuator.py with an ACTUATOR export
    2. Run: mara generate all
"""

from ...discovery import DiscoveryConfig, discover_defs
from ..core import ActuatorDef

_config = DiscoveryConfig(
    export_name="ACTUATOR",
    expected_type=ActuatorDef,
    key_attr="name",
    unique_attrs=("name",),
    on_import_error="error",
)

ACTUATORS = discover_defs(__file__, __name__, _config)

__all__ = ["ACTUATORS"]
