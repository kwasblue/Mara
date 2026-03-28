# schema/telemetry/_perf.py
"""MCU performance and watchdog metrics telemetry section."""

from .core import TelemetrySectionDef, FieldDef

SECTION = TelemetrySectionDef(
    name="TELEM_PERF",
    section_id=0x07,
    description="MCU performance and watchdog metrics",
    fields=(
        FieldDef.uint8("last_fault"),
        FieldDef.uint32("hb_count", description="Heartbeat count"),
        FieldDef.uint32("hb_timeouts", description="Heartbeat timeouts"),
        FieldDef.uint32("hb_recoveries", description="Heartbeat recoveries"),
        FieldDef.uint32("hb_max_gap_ms", description="Max heartbeat gap in ms"),
        FieldDef.uint32("motion_cmds", description="Motion commands received"),
        FieldDef.uint32("motion_timeouts", description="Motion timeouts"),
        FieldDef.uint32("motion_max_gap_ms", description="Max motion gap in ms"),
        FieldDef.uint32("iterations", description="Loop iterations"),
        FieldDef.uint32("overruns", description="Loop overruns"),
        FieldDef.uint16("avg_total_us", description="Average loop time in us"),
        FieldDef.uint16("peak_total_us", description="Peak loop time in us"),
        FieldDef.uint16("pkt_last_bytes", description="Last packet bytes"),
        FieldDef.uint16("pkt_max_bytes", description="Max packet bytes"),
        FieldDef.uint32("pkt_sent", description="Packets sent"),
        FieldDef.uint32("pkt_bytes", description="Total bytes sent"),
        FieldDef.uint32("pkt_dropped_sections", description="Dropped sections"),
        FieldDef.uint8("pkt_last_sections", description="Last section count"),
        FieldDef.uint8("pkt_max_sections", description="Max section count"),
        FieldDef.uint8("pkt_buffered", description="Buffered packets"),
    ),
)
