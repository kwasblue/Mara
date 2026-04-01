# schema/telemetry/discovery.py
"""Auto-discovery for telemetry section definitions using unified framework."""

from __future__ import annotations

from typing import Dict

from ..discovery import discover_defs, DiscoveryConfig
from .core import TelemetrySectionDef


def discover_sections(package_file: str, package_name: str) -> Dict[str, TelemetrySectionDef]:
    """
    Auto-discover telemetry section definitions from _*.py files.

    Uses unified discovery framework with uniqueness validation for
    both section names and section IDs.

    Args:
        package_file: __file__ of the package
        package_name: __name__ of the package

    Returns:
        Dictionary mapping section names to TelemetrySectionDef objects

    Raises:
        ValueError: If duplicate section names or IDs are found
        TypeError: If SECTION export is not a TelemetrySectionDef
    """
    config = DiscoveryConfig(
        export_name="SECTION",
        expected_type=TelemetrySectionDef,
        key_attr="name",
        unique_attrs=("name", "section_id"),
        on_import_error="error",
    )
    return discover_defs(package_file, package_name, config)


__all__ = ["discover_sections"]
