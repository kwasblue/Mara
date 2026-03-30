"""Tests for typed persistence record classes."""

import pytest
from mara_host.services.persistence.types import (
    CalibrationRecord,
    DiagnosticRecord,
    ControlGraphPayload,
    CalibrationData,
    DiagnosticData,
)


class TestCalibrationRecord:
    def test_from_dict(self):
        data = {
            "type": "encoder",
            "saved_at": 1234567890.0,
            "values": {"ticks_per_rev": 400, "offset": 0.5},
        }
        record = CalibrationRecord.from_dict("motor_0", data)

        assert record.name == "motor_0"
        assert record.calibration_type == "encoder"
        assert record.saved_at == 1234567890.0
        assert record.values["ticks_per_rev"] == 400

    def test_to_dict_roundtrip(self):
        record = CalibrationRecord(
            name="servo_1",
            calibration_type="servo",
            saved_at=1000.0,
            values={"min_angle": 0, "max_angle": 180},
        )
        result = record.to_dict()

        assert result["type"] == "servo"
        assert result["saved_at"] == 1000.0
        assert result["values"]["min_angle"] == 0

    def test_immutable(self):
        record = CalibrationRecord(
            name="test",
            calibration_type="generic",
            saved_at=0.0,
            values={},
        )
        with pytest.raises(AttributeError):
            record.name = "changed"


class TestDiagnosticRecord:
    def test_from_dict(self):
        data = {
            "name": "imu_check",
            "captured_at": 999.0,
            "details": {"pitch": 10.5, "roll": 2.0},
        }
        record = DiagnosticRecord.from_dict(data)

        assert record.name == "imu_check"
        assert record.captured_at == 999.0
        assert record.details["pitch"] == 10.5

    def test_to_dict(self):
        record = DiagnosticRecord(
            name="motor_test",
            captured_at=500.0,
            details={"speed": 0.75, "current": 1.2},
        )
        result = record.to_dict()

        assert result["name"] == "motor_test"
        assert result["details"]["speed"] == 0.75


class TestControlGraphPayload:
    def test_from_dict(self):
        data = {
            "version": 2,
            "saved_at": 12345.0,
            "source": "mcp",
            "graph": {"slots": []},
        }
        payload = ControlGraphPayload.from_dict(data)

        assert payload.version == 2
        assert payload.source == "mcp"
        assert payload.graph == {"slots": []}

    def test_to_dict_includes_kind(self):
        payload = ControlGraphPayload(
            version=1,
            saved_at=100.0,
            source="cli",
            graph={"slots": [{"id": "test"}]},
        )
        result = payload.to_dict()

        assert result["kind"] == "control_graph"
        assert result["version"] == 1
        assert result["source"] == "cli"


class TestCalibrationData:
    def test_from_empty_dict(self):
        data = CalibrationData.from_dict({})
        assert data.version == 1
        assert data.records == {}

    def test_from_dict_with_records(self):
        data = {
            "version": 2,
            "records": {
                "motor_0": {
                    "type": "encoder",
                    "saved_at": 1000.0,
                    "values": {"offset": 0.1},
                },
                "motor_1": {
                    "type": "encoder",
                    "saved_at": 2000.0,
                    "values": {"offset": 0.2},
                },
            },
        }
        store = CalibrationData.from_dict(data)

        assert store.version == 2
        assert len(store.records) == 2
        assert store.get("motor_0").values["offset"] == 0.1

    def test_set_and_get(self):
        store = CalibrationData()
        record = CalibrationRecord(
            name="test",
            calibration_type="generic",
            saved_at=0.0,
            values={"key": "value"},
        )
        store.set(record)

        assert store.get("test") == record
        assert store.get("nonexistent") is None

    def test_to_dict(self):
        store = CalibrationData(version=1)
        store.set(CalibrationRecord(
            name="cal_1",
            calibration_type="servo",
            saved_at=100.0,
            values={"angle": 90},
        ))
        result = store.to_dict()

        assert result["kind"] == "calibrations"
        assert "cal_1" in result["records"]


class TestDiagnosticData:
    def test_from_empty_dict(self):
        data = DiagnosticData.from_dict({})
        assert data.version == 1
        assert data.records == []

    def test_append(self):
        store = DiagnosticData()
        record = DiagnosticRecord(
            name="test",
            captured_at=123.0,
            details={"status": "ok"},
        )
        store.append(record)

        assert len(store.records) == 1
        assert store.records[0].name == "test"

    def test_to_dict(self):
        store = DiagnosticData()
        store.append(DiagnosticRecord(
            name="check_1",
            captured_at=1.0,
            details={},
        ))
        result = store.to_dict()

        assert result["kind"] == "diagnostics"
        assert len(result["records"]) == 1
