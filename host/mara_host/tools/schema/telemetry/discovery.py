# schema/telemetry/discovery.py
"""Auto-discovery for telemetry section definitions."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict

from .core import TelemetrySectionDef


def discover_sections(package_file: str, package_name: str) -> Dict[str, TelemetrySectionDef]:
    """
    Auto-discover telemetry section definitions from _*.py files.

    Args:
        package_file: __file__ of the package
        package_name: __name__ of the package

    Returns:
        Dictionary mapping section names to TelemetrySectionDef objects
    """
    registry: Dict[str, TelemetrySectionDef] = {}
    package_dir = Path(package_file).parent

    for module_file in sorted(package_dir.glob("_*.py")):
        if module_file.name.startswith("__"):
            continue

        module_name = module_file.stem
        try:
            module = importlib.import_module(f"{package_name}.{module_name}")
        except ImportError as e:
            import warnings
            warnings.warn(f"Failed to import telemetry module {module_name}: {e}")
            continue

        # Look for SECTION export
        section = getattr(module, "SECTION", None)
        if section is None:
            continue

        if not isinstance(section, TelemetrySectionDef):
            raise TypeError(
                f"{package_name}.{module_name}.SECTION must be a TelemetrySectionDef, "
                f"got {type(section).__name__}"
            )

        if section.name in registry:
            raise ValueError(f"Duplicate telemetry section name: {section.name}")

        if any(s.section_id == section.section_id for s in registry.values()):
            existing = next(s for s in registry.values() if s.section_id == section.section_id)
            raise ValueError(
                f"Duplicate telemetry section ID 0x{section.section_id:02X}: "
                f"{section.name} and {existing.name}"
            )

        registry[section.name] = section

    return registry


__all__ = ["discover_sections"]
