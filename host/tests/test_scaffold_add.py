# tests/test_scaffold_add.py
"""
Tests for mara add scaffolding command.

Priority: HIGH - This command writes files and mutates mara_build.yaml.
A bug here could corrupt build configuration.
"""

from __future__ import annotations

import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def project_tree(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    # Host directory
    host_dir = tmp_path / "host" / "mara_host"
    host_dir.mkdir(parents=True)
    (host_dir / "__init__.py").write_text("")

    # Services directory
    services_dir = host_dir / "services" / "control"
    services_dir.mkdir(parents=True)
    (services_dir / "__init__.py").write_text("")

    # Firmware directory
    firmware_dir = tmp_path / "firmware" / "mcu"
    (firmware_dir / "include" / "sensor").mkdir(parents=True)
    (firmware_dir / "include" / "motor").mkdir(parents=True)
    (firmware_dir / "src" / "sensor").mkdir(parents=True)

    # Config directory with mara_build.yaml
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    build_yaml = config_dir / "mara_build.yaml"
    build_yaml.write_text(dedent("""\
        # mara_build.yaml

        categories:
          Sensors:
            - ultrasonic
            - imu
          Motors:
            - servo
            - dc_motor

        profiles:
          minimal:
            # Sensors
            ultrasonic: false
            imu: false
            # Motors
            servo: false
            dc_motor: false

          full:
            # Sensors
            ultrasonic: true
            imu: true
            # Motors
            servo: true
            dc_motor: true

        active_profile: full
    """))

    return tmp_path


@pytest.fixture
def add_module():
    """Import the add module."""
    # Import directly to avoid full mara_host dependency chain
    import importlib.util
    add_path = Path(__file__).parent.parent / "mara_host" / "cli" / "commands" / "add.py"
    spec = importlib.util.spec_from_file_location("add", add_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ═══════════════════════════════════════════════════════════════════════════
# File Generation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSensorGeneration:
    """Tests for sensor file generation."""

    def test_gpio_sensor_generates_header_only(self, project_tree: Path, add_module):
        """GPIO sensor should generate only header file, no cpp."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        created = add_module.generate_sensor(
            name="temperature",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="gpio",
        )

        # Should create header and service, no cpp
        assert len(created) == 2

        header = firmware_dir / "include" / "sensor" / "TemperatureSensor.h"
        cpp = firmware_dir / "src" / "sensor" / "TemperatureSensor.cpp"
        service = host_dir / "services" / "control" / "temperature_service.py"

        assert header.exists()
        assert not cpp.exists()
        assert service.exists()

    def test_i2c_sensor_generates_header_and_cpp(self, project_tree: Path, add_module):
        """I2C sensor should generate both header and cpp (Manager pattern)."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        created = add_module.generate_sensor(
            name="pressure",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="i2c",
        )

        # Should create header, cpp, and service
        assert len(created) == 3

        header = firmware_dir / "include" / "sensor" / "PressureManager.h"
        cpp = firmware_dir / "src" / "sensor" / "PressureManager.cpp"
        service = host_dir / "services" / "control" / "pressure_service.py"

        assert header.exists()
        assert cpp.exists()
        assert service.exists()

        # Verify Manager pattern naming
        assert "class PressureManager" in header.read_text()
        assert "PressureManager::begin" in cpp.read_text()

    def test_spi_sensor_generates_header_and_cpp(self, project_tree: Path, add_module):
        """SPI sensor should generate both header and cpp."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        created = add_module.generate_sensor(
            name="lidar",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="spi",
        )

        header = firmware_dir / "include" / "sensor" / "LidarManager.h"
        cpp = firmware_dir / "src" / "sensor" / "LidarManager.cpp"

        assert header.exists()
        assert cpp.exists()

        # Verify SPI-specific content
        header_content = header.read_text()
        assert "hal::ISPI" in header_content or "hal::ISpi" in header_content


class TestActuatorGeneration:
    """Tests for actuator file generation."""

    def test_actuator_generates_header_only(self, project_tree: Path, add_module):
        """Actuator should generate only header file (matches DcMotorActuator pattern)."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        created = add_module.generate_actuator(
            name="gripper",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
        )

        assert len(created) == 2

        header = firmware_dir / "include" / "motor" / "GripperActuator.h"
        service = host_dir / "services" / "control" / "gripper_service.py"

        assert header.exists()
        assert service.exists()

        # Verify IActuator pattern
        header_content = header.read_text()
        assert "class GripperActuator" in header_content
        assert "IActuator" in header_content
        assert "REGISTER_ACTUATOR" in header_content


# ═══════════════════════════════════════════════════════════════════════════
# YAML Mutation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestYamlMutation:
    """Tests for mara_build.yaml updates."""

    def test_update_adds_sensor_to_categories(self, project_tree: Path, add_module):
        """Sensor should be added to Sensors category."""
        build_yaml = project_tree / "config" / "mara_build.yaml"

        updated = add_module.update_build_yaml(build_yaml, "sensor", "temperature")

        assert updated
        content = build_yaml.read_text()
        assert "temperature" in content

    def test_update_adds_actuator_to_motors_category(self, project_tree: Path, add_module):
        """Actuator should be added to Motors category."""
        build_yaml = project_tree / "config" / "mara_build.yaml"

        updated = add_module.update_build_yaml(build_yaml, "actuator", "gripper")

        assert updated
        content = build_yaml.read_text()
        assert "gripper" in content

    def test_update_is_idempotent(self, project_tree: Path, add_module):
        """Running update twice should not duplicate entries."""
        build_yaml = project_tree / "config" / "mara_build.yaml"

        # First update
        add_module.update_build_yaml(build_yaml, "sensor", "temperature")
        content_after_first = build_yaml.read_text()
        count_first = content_after_first.count("temperature")

        # Second update - should be idempotent
        updated = add_module.update_build_yaml(build_yaml, "sensor", "temperature")

        assert not updated  # Should return False when already exists
        content_after_second = build_yaml.read_text()
        count_second = content_after_second.count("temperature")

        assert count_first == count_second

    def test_update_preserves_yaml_structure(self, project_tree: Path, add_module):
        """YAML should remain valid after update."""
        build_yaml = project_tree / "config" / "mara_build.yaml"

        add_module.update_build_yaml(build_yaml, "sensor", "humidity")

        # Should still be valid YAML
        import yaml
        content = build_yaml.read_text()
        parsed = yaml.safe_load(content)

        assert "categories" in parsed
        assert "profiles" in parsed
        assert "active_profile" in parsed

    def test_update_does_not_corrupt_existing_entries(self, project_tree: Path, add_module):
        """Existing entries should remain intact."""
        build_yaml = project_tree / "config" / "mara_build.yaml"
        original_content = build_yaml.read_text()

        add_module.update_build_yaml(build_yaml, "sensor", "temperature")

        new_content = build_yaml.read_text()

        # Original entries should still exist
        assert "ultrasonic" in new_content
        assert "imu" in new_content
        assert "servo" in new_content
        assert "dc_motor" in new_content


# ═══════════════════════════════════════════════════════════════════════════
# Generated Code Validity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGeneratedCodeValidity:
    """Tests that generated code is syntactically valid."""

    def test_generated_header_is_valid_cpp(self, project_tree: Path, add_module):
        """Generated C++ header should be parseable."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        add_module.generate_sensor(
            name="temperature",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="gpio",
        )

        header = firmware_dir / "include" / "sensor" / "TemperatureSensor.h"
        content = header.read_text()

        # Basic structural checks (can't compile without full toolchain)
        assert "#pragma once" in content
        assert "namespace mara" in content
        assert content.count("{") == content.count("}")
        assert "class TemperatureSensor" in content

    def test_generated_service_imports_cleanly(self, project_tree: Path, add_module):
        """Generated Python service should be syntactically valid."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        add_module.generate_sensor(
            name="temperature",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="gpio",
        )

        service = host_dir / "services" / "control" / "temperature_service.py"

        # Should compile without syntax errors
        import ast
        content = service.read_text()
        ast.parse(content)  # Raises SyntaxError if invalid

    def test_manager_cpp_is_valid(self, project_tree: Path, add_module):
        """Generated Manager cpp should be structurally valid."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        add_module.generate_sensor(
            name="pressure",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="i2c",
        )

        cpp = firmware_dir / "src" / "sensor" / "PressureManager.cpp"
        content = cpp.read_text()

        # Structural checks
        assert "#include" in content
        assert "PressureManager::begin" in content
        assert "PressureManager::readSample" in content
        assert content.count("{") == content.count("}")


# ═══════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_hyphenated_name_converted_to_underscore(self, project_tree: Path, add_module):
        """Names with hyphens should be converted to underscores."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        add_module.generate_sensor(
            name="air-quality",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="gpio",
        )

        # Should use underscore in filename
        header = firmware_dir / "include" / "sensor" / "AirQualitySensor.h"
        service = host_dir / "services" / "control" / "air_quality_service.py"

        assert header.exists()
        assert service.exists()

    def test_existing_file_not_overwritten(self, project_tree: Path, add_module):
        """Existing files should not be overwritten."""
        host_dir = project_tree / "host" / "mara_host"
        firmware_dir = project_tree / "firmware" / "mcu"

        # Create existing file with custom content
        header = firmware_dir / "include" / "sensor" / "TemperatureSensor.h"
        header.write_text("// Custom implementation - do not overwrite")

        created = add_module.generate_sensor(
            name="temperature",
            output_dir=host_dir,
            firmware_dir=firmware_dir,
            bus="gpio",
        )

        # Header should not be in created list
        assert header not in created

        # Content should be preserved
        assert "Custom implementation" in header.read_text()

    def test_class_name_conversion(self, add_module):
        """Name to class conversion should handle various formats."""
        assert add_module.to_class_name("temperature") == "Temperature"
        assert add_module.to_class_name("air_quality") == "AirQuality"
        assert add_module.to_class_name("co2-sensor") == "Co2Sensor"
        assert add_module.to_class_name("PM25") == "Pm25"
