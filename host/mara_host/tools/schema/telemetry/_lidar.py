# schema/telemetry/_lidar.py
"""LiDAR sensor telemetry section definition."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_LIDAR",
    section_id=0x03,
    description="LiDAR distance sensor",
    fields=(
        FieldDef.uint8("online"),
        FieldDef.uint8("ok"),
        FieldDef.uint16("dist_mm", scale=0.001, description="Distance in meters"),
        FieldDef.uint16("signal", description="Signal strength"),
    ),
)
