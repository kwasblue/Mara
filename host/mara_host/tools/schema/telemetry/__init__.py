# schema/telemetry/__init__.py
"""
Telemetry section definitions with auto-discovery.

To add a new telemetry section, create a file `_mysection.py` with a
`SECTION` object of type `TelemetrySectionDef`.

Example:
    # _mysensor.py
    from ..telemetry.core import TelemetrySectionDef, FieldDef

    SECTION = TelemetrySectionDef(
        name="TELEM_MY_SENSOR",
        section_id=0x20,
        description="My sensor telemetry data",
        fields=(
            FieldDef.float32("value"),
            FieldDef.uint8("status"),
        ),
    )

The section will be auto-discovered and available in TELEMETRY_SECTIONS.
"""

from .core import TelemetrySectionDef, FieldDef
from .discovery import discover_sections

TELEMETRY_SECTIONS = discover_sections(__file__, __name__)

__all__ = ["TELEMETRY_SECTIONS", "TelemetrySectionDef", "FieldDef"]
