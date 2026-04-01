# schema/hardware/sensors/__init__.py
"""
Sensor definitions with auto-discovery.

To add a new sensor:
    1. Create _mysensor.py with a SENSOR export
    2. Run: mara generate all
"""

from ...discovery import DiscoveryConfig, discover_defs
from ..core import SensorDef

_config = DiscoveryConfig(
    export_name="SENSOR",
    expected_type=SensorDef,
    key_attr="name",
    unique_attrs=("name",),
    on_import_error="error",
)

SENSORS = discover_defs(__file__, __name__, _config)

__all__ = ["SENSORS"]
