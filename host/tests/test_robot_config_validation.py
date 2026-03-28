# tests/test_robot_config_validation.py
"""Tests for robot configuration schema validation."""

import pytest
import tempfile
from pathlib import Path

import yaml

from mara_host.config import (
    RobotConfig,
    ConfigValidationError,
    validate_config_with_context,
)


class TestSchemaValidation:
    """Test JSON schema validation of robot configs."""

    def test_valid_minimal_config(self):
        """Minimal valid config with just name."""
        data = {"name": "test_robot"}
        errors = validate_config_with_context(data)
        assert errors == []

    def test_valid_full_config(self):
        """Full config with all sections."""
        data = {
            "name": "full_robot",
            "description": "A fully configured robot",
            "type": "mobile_base",
            "transport": {
                "type": "tcp",
                "host": "192.168.1.100",
                "tcp_port": 3333,
            },
            "drive": {
                "type": "differential",
                "wheel_radius": 0.05,
                "wheel_base": 0.2,
                "max_linear_vel": 1.0,
                "max_angular_vel": 3.0,
            },
            "features": {
                "telemetry": True,
                "encoder": True,
                "motion": True,
            },
            "settings": {
                "telemetry_interval_ms": 100,
                "pwm_freq_hz": 1000,
                "control_rate_hz": 50,
            },
            "sensors": {
                "imu": {
                    "kind": "imu",
                    "enabled": True,
                    "transport": "telemetry",
                },
                "ultrasonic": {
                    "kind": "ultrasonic",
                    "sensor_id": 0,
                    "transport": "telemetry",
                },
            },
        }
        errors = validate_config_with_context(data)
        assert errors == []

    def test_valid_joints_config(self):
        """Config with joints for robotic arm."""
        data = {
            "name": "arm_robot",
            "joints": {
                "shoulder": {
                    "type": "revolute",
                    "actuator": "servo",
                    "actuator_id": 0,
                    "pin": 18,
                    "min_angle": 0,
                    "max_angle": 180,
                },
                "elbow": {
                    "type": "revolute",
                    "actuator": "servo",
                    "actuator_id": 1,
                    "parent": "shoulder",
                },
            },
            "chains": {
                "arm": ["shoulder", "elbow"],
            },
        }
        errors = validate_config_with_context(data)
        assert errors == []

    def test_missing_name(self):
        """Name is required."""
        data = {"transport": {"type": "serial", "port": "/dev/ttyUSB0"}}
        errors = validate_config_with_context(data)
        assert len(errors) == 1
        assert "'name' is a required property" in errors[0]

    def test_invalid_name_format(self):
        """Name must be alphanumeric with underscores/hyphens."""
        data = {"name": "invalid name!"}
        errors = validate_config_with_context(data)
        assert len(errors) == 1
        assert "name" in errors[0].lower()

    def test_empty_name(self):
        """Name cannot be empty."""
        data = {"name": ""}
        errors = validate_config_with_context(data)
        assert len(errors) >= 1

    def test_invalid_transport_type(self):
        """Transport type must be serial, tcp, or ble."""
        data = {
            "name": "test",
            "transport": {"type": "bluetooth"},
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1
        assert any("serial" in e or "tcp" in e or "ble" in e for e in errors)

    def test_invalid_baudrate(self):
        """Baudrate must be positive and reasonable."""
        data = {
            "name": "test",
            "transport": {
                "type": "serial",
                "port": "/dev/ttyUSB0",
                "baudrate": 100,  # Too low
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1
        assert any("baudrate" in e.lower() or "9600" in e for e in errors)

    def test_invalid_tcp_port(self):
        """TCP port must be 1-65535."""
        data = {
            "name": "test",
            "transport": {
                "type": "tcp",
                "host": "localhost",
                "tcp_port": 70000,
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1

    def test_invalid_drive_wheel_radius(self):
        """Wheel radius must be positive."""
        data = {
            "name": "test",
            "drive": {
                "wheel_radius": 0,
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1
        assert any("wheel_radius" in e.lower() for e in errors)

    def test_invalid_settings_telemetry_interval(self):
        """Telemetry interval must be >= 10ms."""
        data = {
            "name": "test",
            "settings": {
                "telemetry_interval_ms": 5,
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1

    def test_invalid_sensor_transport(self):
        """Sensor transport must be telemetry, command, or service."""
        data = {
            "name": "test",
            "sensors": {
                "imu": {
                    "kind": "imu",
                    "transport": "websocket",
                },
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1
        assert any("transport" in e.lower() for e in errors)

    def test_invalid_joint_actuator(self):
        """Joint actuator must be servo, dc_motor, or stepper."""
        data = {
            "name": "test",
            "joints": {
                "arm": {
                    "actuator": "hydraulic",
                    "actuator_id": 0,
                },
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1

    def test_joint_missing_required_fields(self):
        """Joint requires actuator and actuator_id."""
        data = {
            "name": "test",
            "joints": {
                "arm": {
                    "type": "revolute",
                    "pin": 18,
                },
            },
        }
        errors = validate_config_with_context(data)
        assert len(errors) >= 1
        assert any("actuator" in e.lower() for e in errors)


class TestRobotConfigLoad:
    """Test RobotConfig.load() with validation."""

    def test_load_valid_config(self, tmp_path):
        """Loading a valid config succeeds."""
        config_path = tmp_path / "robot.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "name": "test_robot",
                    "transport": {"type": "tcp", "host": "localhost"},
                }
            )
        )

        config = RobotConfig.load(config_path)
        assert config.name == "test_robot"
        assert config.transport.type == "tcp"
        assert config.transport.host == "localhost"

    def test_load_invalid_config_raises(self, tmp_path):
        """Loading an invalid config raises ConfigValidationError."""
        config_path = tmp_path / "robot.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "transport": {"type": "serial", "port": "/dev/ttyUSB0"},
                }
            )
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            RobotConfig.load(config_path)

        assert "name" in str(exc_info.value).lower()
        assert len(exc_info.value.errors) >= 1

    def test_load_skip_validation(self, tmp_path):
        """Can skip validation with validate=False."""
        config_path = tmp_path / "robot.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "transport": {"type": "serial", "port": "/dev/ttyUSB0"},
                }
            )
        )

        # Should not raise with validate=False
        config = RobotConfig.load(config_path, validate=False)
        assert config.name == "robot"  # Default name

    def test_from_dict_validates(self):
        """from_dict() validates by default."""
        with pytest.raises(ConfigValidationError):
            RobotConfig.from_dict({"invalid": "config"})

    def test_from_dict_skip_validation(self):
        """from_dict() can skip validation."""
        config = RobotConfig.from_dict({"invalid": "config"}, validate=False)
        assert config.name == "robot"


class TestExistingConfigs:
    """Test that existing robot configs pass validation."""

    @pytest.fixture
    def robots_dir(self):
        """Get the robots directory path."""
        return Path(__file__).parent.parent / "mara_host" / "robots"

    def test_test_rig_config(self, robots_dir):
        """test_rig.yaml passes validation."""
        config_path = robots_dir / "test_rig.yaml"
        if config_path.exists():
            config = RobotConfig.load(config_path)
            assert config.name == "test_rig"

    def test_arm_3dof_config(self, robots_dir):
        """arm_3dof.yaml passes validation."""
        config_path = robots_dir / "arm_3dof.yaml"
        if config_path.exists():
            config = RobotConfig.load(config_path)
            assert config.name == "arm_3dof"


class TestConfigValidationError:
    """Test ConfigValidationError exception."""

    def test_error_has_errors_list(self):
        """ConfigValidationError contains errors list."""
        err = ConfigValidationError("Test error", errors=["error1", "error2"])
        assert err.errors == ["error1", "error2"]
        assert "Test error" in str(err)

    def test_error_without_errors_list(self):
        """ConfigValidationError works without errors list."""
        err = ConfigValidationError("Test error")
        assert err.errors == []
