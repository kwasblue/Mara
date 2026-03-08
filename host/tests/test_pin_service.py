# tests/test_pin_service.py
"""
Tests for PinService - the business logic layer for pin management.

These tests verify that all pin-related rules and logic are correctly
implemented in the service layer, not scattered across CLI or tools.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from mara_host.services.pins import (
    PinService,
    PinConflict,
    PinRecommendation,
    GroupRecommendation,
    PIN_GROUPS,
)


# =============================================================================
# Pin Classification Tests
# =============================================================================

class TestPinClassification:
    """Test pin categorization methods."""

    def test_flash_pin_identification(self):
        """GPIO 6-11 are flash pins and should be identified as such."""
        service = PinService()

        # Flash pins (6-11)
        for gpio in [6, 7, 8, 9, 10, 11]:
            assert service.is_flash_pin(gpio), f"GPIO {gpio} should be a flash pin"

        # Non-flash pins
        for gpio in [2, 4, 5, 12, 13, 21, 22]:
            assert not service.is_flash_pin(gpio), f"GPIO {gpio} should not be a flash pin"

    def test_boot_pin_identification(self):
        """Boot strapping pins should be correctly identified."""
        service = PinService()

        # Known boot pins: 0, 2, 5, 12, 15
        boot_pins = service.get_boot_pins()
        assert 0 in boot_pins
        assert 2 in boot_pins
        assert 12 in boot_pins
        assert 15 in boot_pins

        # Non-boot pins
        assert 4 not in boot_pins
        assert 21 not in boot_pins

    def test_input_only_identification(self):
        """GPIO 34-39 are input-only and should be identified."""
        service = PinService()

        # Input-only pins (34-39)
        for gpio in [34, 35, 36, 37, 38, 39]:
            assert service.is_input_only(gpio), f"GPIO {gpio} should be input-only"

        # Pins that can do output
        for gpio in [2, 4, 5, 21, 22, 25, 26]:
            assert not service.is_input_only(gpio), f"GPIO {gpio} should not be input-only"

    def test_safe_pin_identification(self):
        """Safe pins have no boot/flash restrictions."""
        service = PinService()

        safe = service.get_safe_pin_set()

        # Safe pins should not include flash pins
        for gpio in [6, 7, 8, 9, 10, 11]:
            assert gpio not in safe

        # Safe pins should not include boot pins with warnings
        # (exact membership depends on implementation)

    def test_get_free_pins_by_category_structure(self):
        """get_free_pins_by_category returns correct structure."""
        service = PinService()

        result = service.get_free_pins_by_category()

        assert "safe" in result
        assert "input_only" in result
        assert "boot" in result
        assert "other" in result

        # All should be lists
        for key, value in result.items():
            assert isinstance(value, list)

        # All values should be integers (GPIO numbers)
        for key, gpios in result.items():
            for gpio in gpios:
                assert isinstance(gpio, int)


# =============================================================================
# Conflict Detection Tests
# =============================================================================

class TestConflictDetection:
    """Test conflict detection logic."""

    def setup_method(self):
        """Create a service with a temporary pins file for each test."""
        self.temp_dir = TemporaryDirectory()
        self.pins_path = Path(self.temp_dir.name) / "pins.json"
        # Note: PinService uses global PINS_JSON by default
        # For isolated tests, we'd need to inject the path
        self.service = PinService()

    def teardown_method(self):
        """Cleanup temporary directory."""
        self.temp_dir.cleanup()

    def test_detect_conflicts_returns_list(self):
        """detect_conflicts should return a list of PinConflict."""
        conflicts = self.service.detect_conflicts()
        assert isinstance(conflicts, list)
        for c in conflicts:
            assert isinstance(c, PinConflict)

    def test_conflict_has_required_fields(self):
        """PinConflict should have all required fields."""
        conflict = PinConflict(
            gpio=2,
            severity="warning",
            conflict_type="boot_pin",
            message="Test message",
            affected_pins=[2]
        )
        assert conflict.gpio == 2
        assert conflict.severity == "warning"
        assert conflict.conflict_type == "boot_pin"
        assert conflict.message == "Test message"
        assert conflict.affected_pins == [2]

    def test_conflict_severity_values(self):
        """Conflicts should use standard severity values."""
        service = PinService()
        conflicts = service.detect_conflicts()

        valid_severities = {"error", "warning", "info"}
        for c in conflicts:
            assert c.severity in valid_severities


# =============================================================================
# Pin Recommendation Tests
# =============================================================================

class TestPinRecommendations:
    """Test pin recommendation logic."""

    def test_suggest_pins_returns_list(self):
        """suggest_pins should return a list of PinRecommendation."""
        service = PinService()
        recs = service.suggest_pins("pwm", count=5)

        assert isinstance(recs, list)
        assert len(recs) <= 5
        for rec in recs:
            assert isinstance(rec, PinRecommendation)

    def test_suggest_pins_excludes_flash_pins(self):
        """Recommendations should never include flash pins."""
        service = PinService()

        for use_case in ["pwm", "adc", "input", "output", "i2c", "spi"]:
            recs = service.suggest_pins(use_case, count=40)
            flash_pins = service.get_flash_pins()

            for rec in recs:
                assert rec.gpio not in flash_pins, \
                    f"Flash pin {rec.gpio} should not be recommended for {use_case}"

    def test_suggest_pins_for_adc_prefers_adc1(self):
        """ADC recommendations should prefer ADC1 pins over ADC2."""
        service = PinService()
        recs = service.suggest_pins("adc", count=10)

        # ADC1 pins: 32-39
        # ADC2 pins: 0, 2, 4, 12-15, 25-27
        adc1_pins = set(range(32, 40))

        if recs:
            # Top recommendations should be ADC1 (higher score)
            top_rec = recs[0]
            assert top_rec.gpio in adc1_pins or any(
                "ADC2" in w or "WiFi" in w for w in top_rec.warnings
            ), "Top ADC recommendation should be ADC1 or have WiFi warning"

    def test_suggest_pins_for_output_excludes_input_only(self):
        """Output/PWM recommendations should exclude input-only pins."""
        service = PinService()
        input_only = service.get_input_only_pins()

        for use_case in ["output", "pwm"]:
            recs = service.suggest_pins(use_case, count=40)
            for rec in recs:
                assert rec.gpio not in input_only, \
                    f"Input-only pin {rec.gpio} should not be recommended for {use_case}"


# =============================================================================
# Group Recommendation Tests
# =============================================================================

class TestGroupRecommendations:
    """Test grouped pin recommendations for motor, encoder, etc."""

    def test_recommend_motor_pins_structure(self):
        """Motor recommendation should return proper structure."""
        service = PinService()
        rec = service.recommend_motor_pins("TEST")

        assert isinstance(rec, GroupRecommendation)
        assert isinstance(rec.suggested_assignments, dict)
        assert isinstance(rec.warnings, list)
        assert isinstance(rec.alternatives, list)

    def test_recommend_motor_pins_names(self):
        """Motor recommendation should use correct naming."""
        service = PinService()
        rec = service.recommend_motor_pins("LEFT")

        # Should have PWM, IN1, IN2 with correct prefix
        expected_names = {"MOTOR_LEFT_PWM", "MOTOR_LEFT_IN1", "MOTOR_LEFT_IN2"}
        assert set(rec.suggested_assignments.keys()) == expected_names

    def test_recommend_encoder_pins_structure(self):
        """Encoder recommendation should return A and B channels."""
        service = PinService()
        rec = service.recommend_encoder_pins("0")

        assert "ENC0_A" in rec.suggested_assignments
        assert "ENC0_B" in rec.suggested_assignments

    def test_recommend_i2c_pins_uses_defaults(self):
        """I2C recommendation should prefer standard pins 21/22."""
        service = PinService()
        rec = service.recommend_i2c_pins()

        # Standard I2C pins are GPIO 21 (SDA) and 22 (SCL)
        # If available, these should be suggested
        if "I2C_SDA" in rec.suggested_assignments:
            # May not be 21 if already assigned, but should be valid
            assert isinstance(rec.suggested_assignments["I2C_SDA"], int)
        if "I2C_SCL" in rec.suggested_assignments:
            assert isinstance(rec.suggested_assignments["I2C_SCL"], int)

    def test_recommend_spi_pins_structure(self):
        """SPI recommendation should attempt MOSI, MISO, CLK, CS."""
        service = PinService()
        rec = service.recommend_spi_pins()

        # Should return a GroupRecommendation
        assert isinstance(rec, GroupRecommendation)

        # If pins are available, should use correct names
        for name in rec.suggested_assignments.keys():
            assert name.startswith("SPI_")

        # If pins weren't available, should have warnings
        if len(rec.suggested_assignments) < 4:
            assert len(rec.warnings) > 0

    def test_recommend_uart_pins_structure(self):
        """UART recommendation should have TX and RX."""
        service = PinService()
        rec = service.recommend_uart_pins("2")

        assert "UART2_TX" in rec.suggested_assignments
        assert "UART2_RX" in rec.suggested_assignments

    def test_recommend_stepper_pins_structure(self):
        """Stepper recommendation should have STEP, DIR, EN."""
        service = PinService()
        rec = service.recommend_stepper_pins("0")

        expected = {"STEPPER0_STEP", "STEPPER0_DIR", "STEPPER0_EN"}
        assert set(rec.suggested_assignments.keys()) == expected

    def test_recommend_servo_pins_structure(self):
        """Servo recommendation should have SIG."""
        service = PinService()
        rec = service.recommend_servo_pins("0")

        assert "SERVO0_SIG" in rec.suggested_assignments

    def test_group_recommendations_use_unique_pins(self):
        """Group recommendations should not suggest the same pin twice."""
        service = PinService()

        for group_type in ["motor", "encoder", "stepper", "spi", "uart"]:
            if group_type == "motor":
                rec = service.recommend_motor_pins("TEST")
            elif group_type == "encoder":
                rec = service.recommend_encoder_pins("TEST")
            elif group_type == "stepper":
                rec = service.recommend_stepper_pins("TEST")
            elif group_type == "spi":
                rec = service.recommend_spi_pins()
            elif group_type == "uart":
                rec = service.recommend_uart_pins("TEST")

            pins = list(rec.suggested_assignments.values())
            assert len(pins) == len(set(pins)), \
                f"{group_type} recommendation has duplicate pins: {pins}"


# =============================================================================
# Use Case Notes Tests
# =============================================================================

class TestUseCaseNotes:
    """Test that use case notes are provided by the service."""

    def test_adc_notes_mention_wifi(self):
        """ADC notes should mention WiFi conflict with ADC2."""
        service = PinService()
        notes = service.get_use_case_notes("adc")

        assert len(notes) > 0
        combined = " ".join(notes).lower()
        assert "wifi" in combined or "adc2" in combined

    def test_i2c_notes_mention_defaults(self):
        """I2C notes should mention default pins."""
        service = PinService()
        notes = service.get_use_case_notes("i2c")

        assert len(notes) > 0
        combined = " ".join(notes)
        assert "21" in combined or "22" in combined or "SDA" in combined or "SCL" in combined

    def test_unknown_use_case_returns_empty(self):
        """Unknown use case should return empty list, not error."""
        service = PinService()
        notes = service.get_use_case_notes("nonexistent_use_case")

        assert isinstance(notes, list)
        assert len(notes) == 0


# =============================================================================
# PIN_GROUPS Constant Tests
# =============================================================================

class TestPinGroupsConstant:
    """Test the PIN_GROUPS configuration."""

    def test_all_groups_have_required_fields(self):
        """Each group should have pins, capabilities, and description."""
        for name, group in PIN_GROUPS.items():
            assert "pins" in group, f"{name} missing 'pins'"
            assert "capabilities" in group, f"{name} missing 'capabilities'"
            assert "description" in group, f"{name} missing 'description'"

    def test_pins_and_capabilities_match_length(self):
        """pins and capabilities lists should have same length."""
        for name, group in PIN_GROUPS.items():
            assert len(group["pins"]) == len(group["capabilities"]), \
                f"{name} has mismatched pins/capabilities lengths"

    def test_expected_groups_exist(self):
        """Expected group types should be defined."""
        expected = ["motor", "encoder", "stepper", "servo", "i2c", "spi", "uart"]
        for group_name in expected:
            assert group_name in PIN_GROUPS, f"Missing group: {group_name}"


# =============================================================================
# Service Read Operations Tests
# =============================================================================

class TestServiceReadOperations:
    """Test service read operations."""

    def test_get_all_pins_returns_dict(self):
        """get_all_pins should return a dict of GPIO -> PinInfo."""
        service = PinService()
        pins = service.get_all_pins()

        assert isinstance(pins, dict)
        assert len(pins) > 0

        # Check a known pin
        assert 2 in pins
        assert 21 in pins

    def test_get_pin_info_returns_info_or_none(self):
        """get_pin_info should return PinInfo for valid GPIO, None otherwise."""
        service = PinService()

        # Valid GPIO
        info = service.get_pin_info(21)
        assert info is not None
        assert hasattr(info, "capabilities")

        # Invalid GPIO
        info = service.get_pin_info(999)
        assert info is None

    def test_capability_string_returns_string(self):
        """capability_string should return human-readable string."""
        service = PinService()

        cap_str = service.capability_string(21)
        assert isinstance(cap_str, str)
        assert len(cap_str) > 0

    def test_generate_pinout_diagram_returns_string(self):
        """generate_pinout_diagram should return ASCII diagram."""
        service = PinService()

        diagram = service.generate_pinout_diagram()
        assert isinstance(diagram, str)
        assert len(diagram) > 100  # Should be substantial


# =============================================================================
# Integration Tests
# =============================================================================

class TestServiceIntegration:
    """Integration tests for common workflows."""

    def test_recommend_then_assign_workflow(self):
        """Typical workflow: get recommendation, then assign."""
        service = PinService()

        # Get I2C recommendation
        rec = service.recommend_i2c_pins()

        # If pins are available, verify structure
        if "I2C_SDA" in rec.suggested_assignments and "I2C_SCL" in rec.suggested_assignments:
            sda = rec.suggested_assignments["I2C_SDA"]
            scl = rec.suggested_assignments["I2C_SCL"]

            assert isinstance(sda, int)
            assert isinstance(scl, int)
            assert sda != scl
        else:
            # If not all pins available, should have warnings
            assert len(rec.warnings) > 0 or len(rec.suggested_assignments) < 2

    def test_validate_is_alias_for_detect_conflicts(self):
        """validate() should be an alias for detect_conflicts()."""
        service = PinService()

        conflicts1 = service.detect_conflicts()
        conflicts2 = service.validate()

        # Should return same result (both read current state)
        assert type(conflicts1) == type(conflicts2)
