# tests/test_schema_extensibility.py
"""
Tests for schema extensibility patterns.

Verifies that all schema systems follow consistent patterns:
1. Auto-discovery from _*.py files
2. Uniqueness validation at import time
3. Typed dataclass definitions
4. Legacy dict compatibility via to_dict()/to_legacy_dict()

These tests ensure new extensions are automatically picked up and validated.
"""

from __future__ import annotations

import importlib
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

import pytest


# =============================================================================
# SCHEMA REGISTRY - All schema systems to test
# =============================================================================

SCHEMA_SYSTEMS = [
    {
        "name": "Commands",
        "module": "mara_host.tools.schema.commands",
        "registry_attr": "COMMAND_OBJECTS",
        "item_type_name": "CommandDef",
        "key_attr": None,  # Key is external (dict key)
        "to_dict_method": "to_dict",
        "min_count": 50,  # Should have at least this many
    },
    {
        "name": "Telemetry",
        "module": "mara_host.tools.schema.telemetry",
        "registry_attr": "TELEMETRY_SECTIONS",
        "item_type_name": "TelemetrySectionDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 5,
    },
    {
        "name": "Binary Commands",
        "module": "mara_host.tools.schema.binary",
        "registry_attr": "BINARY_COMMAND_DEFS",
        "item_type_name": "BinaryCommandDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 3,
    },
    {
        "name": "CAN Messages",
        "module": "mara_host.tools.schema.can",
        "registry_attr": "CAN_MESSAGE_DEFS",
        "item_type_name": "CanMessageDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 3,
    },
    {
        "name": "GPIO Channels",
        "module": "mara_host.tools.schema.gpio_channels",
        "registry_attr": "GPIO_CHANNEL_DEFS",
        "item_type_name": "GpioChannelDef",
        "key_attr": "name",
        "to_dict_method": "to_dict",
        "min_count": 3,
    },
    {
        "name": "Control Graph Sources",
        "module": "mara_host.tools.schema.control_graph",
        "registry_attr": "SOURCE_DEFS",
        "item_type_name": "SourceDef",
        "key_attr": "kind",
        "to_dict_method": "to_dict",
        "min_count": 2,
    },
    {
        "name": "Control Graph Transforms",
        "module": "mara_host.tools.schema.control_graph",
        "registry_attr": "TRANSFORM_DEFS",
        "item_type_name": "TransformDef",
        "key_attr": "kind",
        "to_dict_method": "to_dict",
        "min_count": 10,
    },
    {
        "name": "Control Graph Sinks",
        "module": "mara_host.tools.schema.control_graph",
        "registry_attr": "SINK_DEFS",
        "item_type_name": "SinkDef",
        "key_attr": "kind",
        "to_dict_method": "to_dict",
        "min_count": 2,
    },
    {
        "name": "Hardware Sensors",
        "module": "mara_host.tools.schema.hardware",
        "registry_attr": "SENSORS",
        "item_type_name": "SensorDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 3,
    },
    {
        "name": "Hardware Actuators",
        "module": "mara_host.tools.schema.hardware",
        "registry_attr": "ACTUATORS",
        "item_type_name": "ActuatorDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 2,
    },
    {
        "name": "Hardware Transports",
        "module": "mara_host.tools.schema.hardware",
        "registry_attr": "TRANSPORTS",
        "item_type_name": "TransportDef",
        "key_attr": "name",
        "to_dict_method": "to_legacy_dict",
        "min_count": 2,
    },
    {
        "name": "Control Blocks",
        "module": "mara_host.tools.schema.control",
        "registry_attr": "CONTROL_BLOCKS",
        "item_type_name": None,  # Dict-based (legacy)
        "key_attr": None,
        "to_dict_method": None,
        "min_count": 10,
    },
]


def get_schema_ids():
    """Generate test IDs from schema names."""
    return [s["name"] for s in SCHEMA_SYSTEMS]


# =============================================================================
# DISCOVERY TESTS
# =============================================================================


class TestSchemaDiscovery:
    """Test that all schema systems discover definitions correctly."""

    @pytest.mark.parametrize("schema", SCHEMA_SYSTEMS, ids=get_schema_ids())
    def test_schema_imports_successfully(self, schema: dict):
        """Schema module imports without errors."""
        module = importlib.import_module(schema["module"])
        assert module is not None

    @pytest.mark.parametrize("schema", SCHEMA_SYSTEMS, ids=get_schema_ids())
    def test_registry_exists(self, schema: dict):
        """Schema exports the expected registry attribute."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"], None)

        assert registry is not None, f"{schema['module']} missing {schema['registry_attr']}"
        assert isinstance(registry, dict), f"{schema['registry_attr']} should be a dict"

    @pytest.mark.parametrize("schema", SCHEMA_SYSTEMS, ids=get_schema_ids())
    def test_registry_not_empty(self, schema: dict):
        """Registry contains discovered definitions."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        assert len(registry) >= schema["min_count"], (
            f"{schema['name']} should have at least {schema['min_count']} entries, "
            f"got {len(registry)}"
        )

    @pytest.mark.parametrize("schema", SCHEMA_SYSTEMS, ids=get_schema_ids())
    def test_registry_keys_are_strings(self, schema: dict):
        """Registry keys are all strings."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key in registry.keys():
            assert isinstance(key, str), f"Key {key!r} should be a string"


# =============================================================================
# TYPE VALIDATION TESTS
# =============================================================================


class TestSchemaTypes:
    """Test that schema items are properly typed."""

    @pytest.mark.parametrize("schema", SCHEMA_SYSTEMS, ids=get_schema_ids())
    def test_items_are_correct_type(self, schema: dict):
        """Registry items are the expected type (dataclass or dict)."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        if schema["item_type_name"] is None:
            # Legacy dict-based
            for key, item in registry.items():
                assert isinstance(item, dict), f"{key} should be a dict"
        else:
            # Typed dataclass
            item_type = getattr(module, schema["item_type_name"], None)
            if item_type is None:
                # Try importing from core module
                core_module = importlib.import_module(f"{schema['module']}.core")
                item_type = getattr(core_module, schema["item_type_name"])

            for key, item in registry.items():
                assert isinstance(item, item_type), (
                    f"{key} should be {schema['item_type_name']}, got {type(item).__name__}"
                )

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["item_type_name"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["item_type_name"] is not None],
    )
    def test_items_are_dataclasses(self, schema: dict):
        """Typed items are frozen dataclasses."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            assert is_dataclass(item), f"{key} should be a dataclass"

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["item_type_name"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["item_type_name"] is not None],
    )
    def test_dataclasses_are_frozen(self, schema: dict):
        """Typed dataclasses are immutable (frozen=True)."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            # Frozen dataclasses raise FrozenInstanceError on attribute set
            with pytest.raises((AttributeError, TypeError)):
                # Try to set a known attribute - this varies by type
                if hasattr(item, "name"):
                    item.name = "should_fail"
                elif hasattr(item, "kind"):
                    item.kind = "should_fail"
                else:
                    # Skip if no known attribute to test
                    pytest.skip(f"No testable attribute for {key}")


# =============================================================================
# LEGACY COMPATIBILITY TESTS
# =============================================================================


class TestLegacyCompatibility:
    """Test that typed schemas provide legacy dict compatibility."""

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
    )
    def test_items_have_to_dict_method(self, schema: dict):
        """Typed items have a to_dict() or to_legacy_dict() method."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            method = getattr(item, schema["to_dict_method"], None)
            assert method is not None, (
                f"{key} missing {schema['to_dict_method']}() method"
            )
            assert callable(method), (
                f"{key}.{schema['to_dict_method']} should be callable"
            )

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
    )
    def test_to_dict_returns_dict(self, schema: dict):
        """to_dict() methods return a dictionary."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            method = getattr(item, schema["to_dict_method"])
            result = method()

            assert isinstance(result, dict), (
                f"{key}.{schema['to_dict_method']}() should return dict, "
                f"got {type(result).__name__}"
            )

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["to_dict_method"] is not None],
    )
    def test_to_dict_is_json_serializable(self, schema: dict):
        """to_dict() output can be JSON serialized."""
        import json

        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            method = getattr(item, schema["to_dict_method"])
            result = method()

            try:
                json.dumps(result)
            except (TypeError, ValueError) as e:
                pytest.fail(f"{key}.{schema['to_dict_method']}() not JSON serializable: {e}")


# =============================================================================
# UNIQUENESS TESTS
# =============================================================================


class TestSchemaUniqueness:
    """Test that schemas enforce uniqueness constraints."""

    @pytest.mark.parametrize(
        "schema",
        [s for s in SCHEMA_SYSTEMS if s["key_attr"] is not None],
        ids=[s["name"] for s in SCHEMA_SYSTEMS if s["key_attr"] is not None],
    )
    def test_keys_match_item_attribute(self, schema: dict):
        """Registry keys match the item's key attribute (name, kind, etc.)."""
        module = importlib.import_module(schema["module"])
        registry = getattr(module, schema["registry_attr"])

        for key, item in registry.items():
            item_key = getattr(item, schema["key_attr"])
            assert key == item_key, (
                f"Key mismatch: registry key {key!r} != item.{schema['key_attr']} {item_key!r}"
            )

    def test_telemetry_section_ids_unique(self):
        """Telemetry section IDs are unique across all sections."""
        from mara_host.tools.schema.telemetry import TELEMETRY_SECTIONS

        section_ids: dict[int, str] = {}
        for name, section in TELEMETRY_SECTIONS.items():
            sid = section.section_id
            if sid in section_ids:
                pytest.fail(
                    f"Duplicate section_id 0x{sid:02X}: {name} and {section_ids[sid]}"
                )
            section_ids[sid] = name

    def test_binary_command_opcodes_unique(self):
        """Binary command opcodes are unique."""
        from mara_host.tools.schema.binary import BINARY_COMMAND_DEFS

        opcodes: dict[int, str] = {}
        for name, cmd in BINARY_COMMAND_DEFS.items():
            opcode = cmd.opcode
            if opcode in opcodes:
                pytest.fail(
                    f"Duplicate opcode 0x{opcode:02X}: {name} and {opcodes[opcode]}"
                )
            opcodes[opcode] = name

    def test_gpio_channel_ids_unique(self):
        """GPIO channel IDs are unique."""
        from mara_host.tools.schema.gpio_channels import GPIO_CHANNEL_DEFS

        channels: dict[int, str] = {}
        for name, channel in GPIO_CHANNEL_DEFS.items():
            cid = channel.channel
            if cid in channels:
                pytest.fail(
                    f"Duplicate channel {cid}: {name} and {channels[cid]}"
                )
            channels[cid] = name


# =============================================================================
# FILE STRUCTURE TESTS
# =============================================================================


class TestSchemaFileStructure:
    """Test that schema directories follow expected structure."""

    SCHEMA_DIRS = [
        ("commands", "mara_host/tools/schema/commands"),
        ("telemetry", "mara_host/tools/schema/telemetry"),
        ("binary", "mara_host/tools/schema/binary"),
        ("can", "mara_host/tools/schema/can"),
        ("gpio_channels", "mara_host/tools/schema/gpio_channels"),
        ("control_graph", "mara_host/tools/schema/control_graph"),
        ("hardware", "mara_host/tools/schema/hardware"),
        ("control", "mara_host/tools/schema/control"),
    ]

    @pytest.mark.parametrize("name,path", SCHEMA_DIRS, ids=[n for n, _ in SCHEMA_DIRS])
    def test_schema_dir_exists(self, name: str, path: str):
        """Schema directory exists."""
        schema_dir = Path(__file__).parents[1] / path
        assert schema_dir.exists(), f"Schema directory not found: {schema_dir}"

    @pytest.mark.parametrize("name,path", SCHEMA_DIRS, ids=[n for n, _ in SCHEMA_DIRS])
    def test_has_init_py(self, name: str, path: str):
        """Schema directory has __init__.py."""
        schema_dir = Path(__file__).parents[1] / path
        init_file = schema_dir / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in {schema_dir}"

    @pytest.mark.parametrize("name,path", SCHEMA_DIRS, ids=[n for n, _ in SCHEMA_DIRS])
    def test_has_core_py(self, name: str, path: str):
        """Schema directory has core.py with type definitions."""
        schema_dir = Path(__file__).parents[1] / path
        core_file = schema_dir / "core.py"
        # core.py is required for typed schemas
        if name not in ("commands",):  # commands has core.py
            assert core_file.exists(), f"Missing core.py in {schema_dir}"

    @pytest.mark.parametrize("name,path", SCHEMA_DIRS, ids=[n for n, _ in SCHEMA_DIRS])
    def test_has_definition_files(self, name: str, path: str):
        """Schema directory has _*.py definition files."""
        schema_dir = Path(__file__).parents[1] / path
        def_files = list(schema_dir.glob("_*.py"))
        # Filter out __init__.py, __pycache__, etc.
        def_files = [f for f in def_files if not f.name.startswith("__")]

        # Some schemas use subdirectories (hardware, control_graph)
        if not def_files:
            # Check subdirectories
            for subdir in schema_dir.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("_"):
                    def_files.extend(subdir.glob("_*.py"))

        assert len(def_files) > 0, f"No _*.py definition files in {schema_dir}"


# =============================================================================
# GENERATOR INTEGRATION TESTS
# =============================================================================


class TestGeneratorIntegration:
    """Test that generators work with discovered schemas."""

    def test_mara_generate_all_succeeds(self):
        """mara generate all completes without errors."""
        import subprocess
        import sys
        from pathlib import Path

        # Find mara CLI relative to the Python interpreter
        python_path = Path(sys.executable)
        mara_path = python_path.parent / "mara"

        if not mara_path.exists():
            import pytest
            pytest.skip("mara CLI not installed in current environment")

        result = subprocess.run(
            [str(mara_path), "generate", "all"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, (
            f"mara generate all failed:\n{result.stderr}\n{result.stdout}"
        )
        assert "All generators completed successfully" in result.stdout
