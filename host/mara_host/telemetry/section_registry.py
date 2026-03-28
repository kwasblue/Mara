# telemetry/section_registry.py
"""
Registry for telemetry sections with auto-discovery support.

This module provides a unified interface for both legacy sections
(defined in telemetry_sections.py) and new auto-discovered sections
(defined in tools/schema/telemetry/_*.py).

For new sections, just create a file and it's automatically available.
"""

from __future__ import annotations

from typing import Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tools.schema.telemetry.core import TelemetrySectionDef


class SectionRegistry:
    """
    Registry mapping section IDs to their definitions and parsers.

    Supports both:
    - Legacy sections with hardcoded parsers in binary_parser.py
    - New auto-discovered sections with self-contained parsers
    """

    _instance: Optional["SectionRegistry"] = None
    _sections_by_id: Dict[int, "TelemetrySectionDef"]
    _sections_by_name: Dict[str, "TelemetrySectionDef"]
    _initialized: bool = False

    def __new__(cls) -> "SectionRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sections_by_id = {}
            cls._instance._sections_by_name = {}
            cls._instance._initialized = False
        return cls._instance

    def _ensure_initialized(self) -> None:
        """Lazy initialization of discovered sections."""
        if self._initialized:
            return

        try:
            from ..tools.schema.telemetry import TELEMETRY_SECTIONS

            for name, section_def in TELEMETRY_SECTIONS.items():
                self._sections_by_id[section_def.section_id] = section_def
                self._sections_by_name[name] = section_def

        except ImportError:
            # Schema module not available
            pass

        self._initialized = True

    def get_by_id(self, section_id: int) -> Optional["TelemetrySectionDef"]:
        """Get section definition by ID."""
        self._ensure_initialized()
        return self._sections_by_id.get(section_id)

    def get_by_name(self, name: str) -> Optional["TelemetrySectionDef"]:
        """Get section definition by name."""
        self._ensure_initialized()
        return self._sections_by_name.get(name)

    def parse_section(self, section_id: int, body: bytes, ts_ms: int) -> Optional[Dict[str, Any]]:
        """
        Parse a section using its registered definition.

        Returns:
            Parsed dictionary, or None if section not found or parse failed
        """
        section_def = self.get_by_id(section_id)
        if section_def is None:
            return None

        return section_def.parse(body, ts_ms)

    def all_sections(self) -> Dict[str, "TelemetrySectionDef"]:
        """Get all registered sections."""
        self._ensure_initialized()
        return dict(self._sections_by_name)

    def section_ids(self) -> Dict[str, int]:
        """Get mapping of section names to IDs (for telemetry_sections.py compatibility)."""
        self._ensure_initialized()
        return {name: sec.section_id for name, sec in self._sections_by_name.items()}


# Global instance
_registry = SectionRegistry()


def get_section_registry() -> SectionRegistry:
    """Get the global section registry."""
    return _registry


def parse_unknown_section(section_id: int, body: bytes, ts_ms: int) -> Optional[Dict[str, Any]]:
    """
    Try to parse an unknown section using the registry.

    This is used by binary_parser.py as a fallback for sections
    that aren't handled by the hardcoded parser.
    """
    return _registry.parse_section(section_id, body, ts_ms)


__all__ = ["SectionRegistry", "get_section_registry", "parse_unknown_section"]
