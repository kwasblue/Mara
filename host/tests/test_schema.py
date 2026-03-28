# tests/test_schema.py
"""
Schema structure tests.

Validates that the schema package is properly organized and all commands
are correctly merged from domain files.
"""



class TestSchemaPackageStructure:
    """Verify schema package is properly organized."""

    def test_schema_package_exists(self):
        """Schema package should be importable."""
        from mara_host.tools import schema
        assert schema is not None

    def test_commands_importable(self):
        """COMMANDS dict should be importable from schema."""
        from mara_host.tools.schema import COMMANDS
        assert isinstance(COMMANDS, dict)
        assert len(COMMANDS) > 0

    def test_all_schema_exports_available(self):
        """All expected exports should be available from schema."""
        from mara_host.tools.schema import (
            COMMANDS,
            BINARY_COMMANDS,
            TELEMETRY_SECTIONS,
            VERSION,
            CAPABILITIES,
            GPIO_CHANNELS,
            CAN_MESSAGES,
            PINS,
        )
        # Just verify they're importable and not None
        assert COMMANDS is not None
        assert BINARY_COMMANDS is not None
        assert TELEMETRY_SECTIONS is not None
        assert VERSION is not None
        assert CAPABILITIES is not None
        assert GPIO_CHANNELS is not None
        assert CAN_MESSAGES is not None
        assert PINS is not None


class TestCommandsDomainFiles:
    """Verify command domain files are properly merged."""

    def test_commands_has_expected_count(self):
        """COMMANDS should have expected number of commands."""
        from mara_host.tools.schema import COMMANDS
        # Total should be 91 commands across all domains (including WiFi commands)
        assert len(COMMANDS) == 91, f"Expected 91 commands, got {len(COMMANDS)}"

    def test_individual_domain_exports(self):
        """Individual domain exports should be available."""
        from mara_host.tools.schema.commands import (
            SAFETY_COMMANDS,
            RATE_COMMANDS,
            CONTROL_COMMANDS,
            MOTION_COMMANDS,
            GPIO_COMMANDS,
            SERVO_COMMANDS,
            STEPPER_COMMANDS,
            SENSOR_COMMANDS,
            DC_MOTOR_COMMANDS,
            OBSERVER_COMMANDS,
            TELEMETRY_COMMANDS,
            CAMERA_COMMANDS,
            WIFI_COMMANDS,
        )
        # Verify expected counts per domain
        assert len(SAFETY_COMMANDS) == 10, f"SAFETY: expected 10, got {len(SAFETY_COMMANDS)}"
        assert len(RATE_COMMANDS) == 4, f"RATE: expected 4, got {len(RATE_COMMANDS)}"
        assert len(CONTROL_COMMANDS) == 17, f"CONTROL: expected 17, got {len(CONTROL_COMMANDS)}"
        assert len(MOTION_COMMANDS) == 2, f"MOTION: expected 2, got {len(MOTION_COMMANDS)}"
        assert len(GPIO_COMMANDS) == 7, f"GPIO: expected 7, got {len(GPIO_COMMANDS)}"
        assert len(SERVO_COMMANDS) == 4, f"SERVO: expected 4, got {len(SERVO_COMMANDS)}"
        assert len(STEPPER_COMMANDS) == 3, f"STEPPER: expected 3, got {len(STEPPER_COMMANDS)}"
        assert len(SENSOR_COMMANDS) == 7, f"SENSOR: expected 7, got {len(SENSOR_COMMANDS)}"
        assert len(DC_MOTOR_COMMANDS) == 5, f"DC_MOTOR: expected 5, got {len(DC_MOTOR_COMMANDS)}"
        assert len(OBSERVER_COMMANDS) == 6, f"OBSERVER: expected 6, got {len(OBSERVER_COMMANDS)}"
        assert len(TELEMETRY_COMMANDS) == 2, f"TELEMETRY: expected 2, got {len(TELEMETRY_COMMANDS)}"
        assert len(CAMERA_COMMANDS) == 20, f"CAMERA: expected 20, got {len(CAMERA_COMMANDS)}"
        assert len(WIFI_COMMANDS) == 4, f"WIFI: expected 4, got {len(WIFI_COMMANDS)}"

    def test_merged_commands_equals_sum_of_domains(self):
        """Merged COMMANDS should equal sum of all domain dicts."""
        from mara_host.tools.schema import COMMANDS
        from mara_host.tools.schema.commands import (
            SAFETY_COMMANDS,
            RATE_COMMANDS,
            CONTROL_COMMANDS,
            MOTION_COMMANDS,
            GPIO_COMMANDS,
            SERVO_COMMANDS,
            STEPPER_COMMANDS,
            SENSOR_COMMANDS,
            DC_MOTOR_COMMANDS,
            OBSERVER_COMMANDS,
            TELEMETRY_COMMANDS,
            CAMERA_COMMANDS,
            WIFI_COMMANDS,
        )

        total = (
            len(SAFETY_COMMANDS) +
            len(RATE_COMMANDS) +
            len(CONTROL_COMMANDS) +
            len(MOTION_COMMANDS) +
            len(GPIO_COMMANDS) +
            len(SERVO_COMMANDS) +
            len(STEPPER_COMMANDS) +
            len(SENSOR_COMMANDS) +
            len(DC_MOTOR_COMMANDS) +
            len(OBSERVER_COMMANDS) +
            len(TELEMETRY_COMMANDS) +
            len(CAMERA_COMMANDS) +
            len(WIFI_COMMANDS)
        )
        assert len(COMMANDS) == total, (
            f"Merged COMMANDS ({len(COMMANDS)}) != sum of domains ({total})"
        )

    def test_no_duplicate_command_names(self):
        """There should be no duplicate command names across domains."""
        from mara_host.tools.schema.commands import (
            SAFETY_COMMANDS,
            RATE_COMMANDS,
            CONTROL_COMMANDS,
            MOTION_COMMANDS,
            GPIO_COMMANDS,
            SERVO_COMMANDS,
            STEPPER_COMMANDS,
            SENSOR_COMMANDS,
            DC_MOTOR_COMMANDS,
            OBSERVER_COMMANDS,
            TELEMETRY_COMMANDS,
            CAMERA_COMMANDS,
            WIFI_COMMANDS,
        )

        all_domains = [
            ("SAFETY", SAFETY_COMMANDS),
            ("RATE", RATE_COMMANDS),
            ("CONTROL", CONTROL_COMMANDS),
            ("MOTION", MOTION_COMMANDS),
            ("GPIO", GPIO_COMMANDS),
            ("SERVO", SERVO_COMMANDS),
            ("STEPPER", STEPPER_COMMANDS),
            ("SENSOR", SENSOR_COMMANDS),
            ("DC_MOTOR", DC_MOTOR_COMMANDS),
            ("OBSERVER", OBSERVER_COMMANDS),
            ("TELEMETRY", TELEMETRY_COMMANDS),
            ("CAMERA", CAMERA_COMMANDS),
            ("WIFI", WIFI_COMMANDS),
        ]

        seen = {}
        duplicates = []

        for domain_name, commands in all_domains:
            for cmd_name in commands.keys():
                if cmd_name in seen:
                    duplicates.append(f"{cmd_name} in both {seen[cmd_name]} and {domain_name}")
                else:
                    seen[cmd_name] = domain_name

        assert not duplicates, f"Duplicate commands found: {duplicates}"


class TestCommandDefinitionFormat:
    """Verify command definitions follow the expected format."""

    def test_all_commands_have_required_fields(self):
        """All commands must have kind, direction, and description."""
        from mara_host.tools.schema import COMMANDS

        required_fields = ["kind", "direction", "description"]
        missing = []

        for cmd_name, cmd_def in COMMANDS.items():
            for field in required_fields:
                if field not in cmd_def:
                    missing.append(f"{cmd_name} missing '{field}'")

        assert not missing, f"Commands missing required fields: {missing}"

    def test_all_commands_have_valid_kind(self):
        """All commands should have kind='cmd'."""
        from mara_host.tools.schema import COMMANDS

        invalid = []
        for cmd_name, cmd_def in COMMANDS.items():
            if cmd_def.get("kind") != "cmd":
                invalid.append(f"{cmd_name} has kind='{cmd_def.get('kind')}'")

        assert not invalid, f"Commands with invalid kind: {invalid}"

    def test_all_commands_have_valid_direction(self):
        """All commands should have valid direction."""
        from mara_host.tools.schema import COMMANDS

        valid_directions = ["host->mcu", "mcu->host", "host->camera"]
        invalid = []

        for cmd_name, cmd_def in COMMANDS.items():
            direction = cmd_def.get("direction")
            if direction not in valid_directions:
                invalid.append(f"{cmd_name} has direction='{direction}'")

        assert not invalid, f"Commands with invalid direction: {invalid}"

    def test_command_names_follow_convention(self):
        """All command names should start with CMD_."""
        from mara_host.tools.schema import COMMANDS

        invalid = []
        for cmd_name in COMMANDS.keys():
            if not cmd_name.startswith("CMD_"):
                invalid.append(cmd_name)

        assert not invalid, f"Commands not starting with CMD_: {invalid}"


class TestSampleCommands:
    """Verify some sample commands exist and are correctly defined."""

    def test_identity_command_exists(self):
        """CMD_GET_IDENTITY should exist in safety commands."""
        from mara_host.tools.schema.commands import SAFETY_COMMANDS
        assert "CMD_GET_IDENTITY" in SAFETY_COMMANDS
        assert SAFETY_COMMANDS["CMD_GET_IDENTITY"]["direction"] == "host->mcu"

    def test_heartbeat_command_exists(self):
        """CMD_HEARTBEAT should exist in safety commands."""
        from mara_host.tools.schema.commands import SAFETY_COMMANDS
        assert "CMD_HEARTBEAT" in SAFETY_COMMANDS

    def test_dc_motor_commands_exist(self):
        """DC motor commands should exist."""
        from mara_host.tools.schema.commands import DC_MOTOR_COMMANDS
        assert "CMD_DC_SET_SPEED" in DC_MOTOR_COMMANDS
        assert "CMD_DC_STOP" in DC_MOTOR_COMMANDS
        assert "CMD_DC_VEL_PID_ENABLE" in DC_MOTOR_COMMANDS

    def test_camera_commands_exist(self):
        """Camera commands should exist."""
        from mara_host.tools.schema.commands import CAMERA_COMMANDS
        assert "CMD_CAM_GET_STATUS" in CAMERA_COMMANDS
        assert "CMD_CAM_SET_RESOLUTION" in CAMERA_COMMANDS
        assert "CMD_CAM_START_CAPTURE" in CAMERA_COMMANDS


class TestSchemaIntegration:
    """Test that schema integrates properly with the rest of the system."""

    def test_schema_exports_match_init_all(self):
        """Schema __all__ should match actual exports."""
        from mara_host.tools import schema

        for name in schema.__all__:
            assert hasattr(schema, name), f"'{name}' in __all__ but not exported"

    def test_commands_package_exports_match_init_all(self):
        """Commands package __all__ should match actual exports."""
        from mara_host.tools.schema import commands

        for name in commands.__all__:
            assert hasattr(commands, name), f"'{name}' in __all__ but not exported"
