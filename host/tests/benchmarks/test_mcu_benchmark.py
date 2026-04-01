# tests/benchmarks/test_mcu_benchmark.py
"""Unit tests for MCU benchmark host integration."""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, Optional


# =============================================================================
# Test Catalog Tests
# =============================================================================


class TestTestCatalog:
    """Tests for test_catalog module."""

    def test_test_id_enum_values(self):
        """Verify TestId enum has expected values."""
        from mara_host.benchmarks.mcu.test_catalog import TestId

        assert TestId.LOOP_TIMING == 0x01
        assert TestId.SIGNAL_BUS_LATENCY == 0x02
        assert TestId.PING_INTERNAL == 0x20
        assert TestId.PID_STEP == 0x30
        assert TestId.UNKNOWN == 0xFF

    def test_bench_state_enum_values(self):
        """Verify BenchState enum has expected values."""
        from mara_host.benchmarks.mcu.test_catalog import BenchState

        assert BenchState.IDLE == 0
        assert BenchState.RUNNING == 1
        assert BenchState.COMPLETE == 2
        assert BenchState.ERROR == 3
        assert BenchState.QUEUED == 4

    def test_bench_error_enum_values(self):
        """Verify BenchError enum has expected values."""
        from mara_host.benchmarks.mcu.test_catalog import BenchError

        assert BenchError.NONE == 0
        assert BenchError.UNKNOWN_TEST == 1
        assert BenchError.CANCELLED == 6

    def test_get_test_name_known(self):
        """get_test_name returns name for known test IDs."""
        from mara_host.benchmarks.mcu.test_catalog import get_test_name, TestId

        assert get_test_name(TestId.LOOP_TIMING) == "LOOP_TIMING"
        assert get_test_name(TestId.PID_STEP) == "PID_STEP"

    def test_get_test_name_unknown(self):
        """get_test_name returns hex string for unknown test IDs."""
        from mara_host.benchmarks.mcu.test_catalog import get_test_name

        assert get_test_name(0xFE) == "TEST_0xFE"

    def test_get_test_description_known(self):
        """get_test_description returns description for known test IDs."""
        from mara_host.benchmarks.mcu.test_catalog import get_test_description, TestId

        desc = get_test_description(TestId.LOOP_TIMING)
        assert desc is not None
        assert "loop" in desc.lower() or "overhead" in desc.lower()

    def test_get_test_description_unknown(self):
        """get_test_description returns None for unknown test IDs."""
        from mara_host.benchmarks.mcu.test_catalog import get_test_description

        assert get_test_description(0xFE) is None

    def test_test_catalog_has_expected_entries(self):
        """TEST_CATALOG contains expected test entries."""
        from mara_host.benchmarks.mcu.test_catalog import TEST_CATALOG, TestId

        assert TestId.LOOP_TIMING in TEST_CATALOG
        assert TestId.SIGNAL_BUS_LATENCY in TEST_CATALOG
        assert TestId.PID_STEP in TEST_CATALOG

    def test_test_info_fields(self):
        """TestInfo dataclass has expected fields."""
        from mara_host.benchmarks.mcu.test_catalog import TEST_CATALOG, TestId

        info = TEST_CATALOG[TestId.LOOP_TIMING]
        assert info.id == TestId.LOOP_TIMING
        assert info.name == "LOOP_TIMING"
        assert info.description is not None
        assert isinstance(info.rt_safe, bool)
        assert isinstance(info.boot_test, bool)


# =============================================================================
# MCU Benchmark Result Tests
# =============================================================================


class TestMCUBenchmarkResult:
    """Tests for MCUBenchmarkResult dataclass."""

    def test_from_dict_basic(self):
        """MCUBenchmarkResult.from_dict parses basic fields."""
        from mara_host.benchmarks.mcu.triggered_benchmark import MCUBenchmarkResult
        from mara_host.benchmarks.mcu.test_catalog import BenchState, BenchError

        data = {
            "test_id": 0x01,
            "state": 2,
            "error": 0,
            "mean_us": 1000,
            "min_us": 500,
            "max_us": 2000,
            "p50_us": 900,
            "p95_us": 1500,
            "p99_us": 1800,
            "jitter_us": 200,
            "total_us": 100000,
            "samples": 100,
            "budget_violations": 0,
            "timestamp_ms": 12345,
        }

        result = MCUBenchmarkResult.from_dict(data)

        assert result.test_id == 0x01
        assert result.state == BenchState.COMPLETE
        assert result.error == BenchError.NONE
        assert result.mean_us == 1000
        assert result.samples == 100

    def test_from_dict_computes_milliseconds(self):
        """MCUBenchmarkResult computes millisecond values."""
        from mara_host.benchmarks.mcu.triggered_benchmark import MCUBenchmarkResult

        data = {
            "test_id": 0x01,
            "state": 2,
            "error": 0,
            "mean_us": 1500,
            "min_us": 500,
            "max_us": 2000,
            "p50_us": 900,
            "p95_us": 1500,
            "p99_us": 1800,
            "jitter_us": 200,
            "total_us": 100000,
            "samples": 100,
            "budget_violations": 0,
        }

        result = MCUBenchmarkResult.from_dict(data)

        assert result.mean_ms == pytest.approx(1.5, rel=0.01)
        assert result.p99_ms == pytest.approx(1.8, rel=0.01)

    def test_from_dict_handles_missing_optional_fields(self):
        """MCUBenchmarkResult handles missing optional fields."""
        from mara_host.benchmarks.mcu.triggered_benchmark import MCUBenchmarkResult

        data = {
            "test_id": 0x01,
            "state": 2,
            "error": 0,
        }

        result = MCUBenchmarkResult.from_dict(data)

        assert result.test_id == 0x01
        assert result.mean_us == 0
        assert result.throughput_hz is None

    def test_str_format(self):
        """MCUBenchmarkResult.__str__ produces readable output."""
        from mara_host.benchmarks.mcu.triggered_benchmark import MCUBenchmarkResult

        data = {
            "test_id": 0x01,
            "state": 2,
            "error": 0,
            "mean_us": 1000,
            "min_us": 500,
            "max_us": 2000,
            "p50_us": 900,
            "p95_us": 1500,
            "p99_us": 1800,
            "jitter_us": 200,
            "total_us": 100000,
            "samples": 100,
            "budget_violations": 0,
            "throughput_hz": 1000.5,
        }

        result = MCUBenchmarkResult.from_dict(data)
        output = str(result)

        assert "LOOP_TIMING" in output
        assert "samples: 100" in output
        assert "throughput" in output.lower()


# =============================================================================
# Perf Metrics Tests
# =============================================================================


class TestPerfMetrics:
    """Tests for PerfMetrics dataclass."""

    def test_from_telemetry(self):
        """PerfMetrics.from_telemetry parses telemetry data."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfMetrics

        data = {
            "hb_count": 100,
            "hb_timeouts": 2,
            "iterations": 50000,
            "overruns": 5,
            "avg_total_us": 450,
            "peak_total_us": 1200,
            "pkt_sent": 1000,
            "pkt_bytes": 50000,
        }

        metrics = PerfMetrics.from_telemetry(data)

        assert metrics.hb_count == 100
        assert metrics.hb_timeouts == 2
        assert metrics.iterations == 50000
        assert metrics.overruns == 5
        assert metrics.avg_total_us == 450
        assert metrics.peak_total_us == 1200

    def test_to_dict(self):
        """PerfMetrics.to_dict produces serializable output."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfMetrics

        data = {
            "hb_count": 100,
            "iterations": 50000,
            "avg_total_us": 450,
        }

        metrics = PerfMetrics.from_telemetry(data)
        output = metrics.to_dict()

        assert "timestamp" in output
        assert "heartbeat" in output
        assert "loop" in output
        assert output["loop"]["iterations"] == 50000

    def test_str_format(self):
        """PerfMetrics.__str__ produces readable output."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfMetrics

        data = {
            "iterations": 50000,
            "overruns": 5,
            "avg_total_us": 450,
            "peak_total_us": 1200,
        }

        metrics = PerfMetrics.from_telemetry(data)
        output = str(metrics)

        assert "450us" in output
        assert "1200us" in output


# =============================================================================
# Perf Session Tests
# =============================================================================


class TestPerfSession:
    """Tests for PerfSession."""

    def test_add_sample(self):
        """PerfSession tracks samples."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfMetrics, PerfSession

        session = PerfSession()
        assert len(session.samples) == 0

        metrics = PerfMetrics.from_telemetry({"avg_total_us": 100})
        session.add_sample(metrics)

        assert len(session.samples) == 1
        assert session.start_time is not None

    def test_get_summary(self):
        """PerfSession.get_summary computes statistics."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfMetrics, PerfSession

        session = PerfSession()

        # Add samples with varying avg_us
        for avg_us in [100, 150, 200, 150, 100]:
            metrics = PerfMetrics.from_telemetry({"avg_total_us": avg_us})
            session.add_sample(metrics)

        summary = session.get_summary()

        assert summary["sample_count"] == 5
        assert "loop_avg_us" in summary
        assert summary["loop_avg_us"]["mean"] == 140.0  # (100+150+200+150+100)/5

    def test_empty_session_summary(self):
        """PerfSession.get_summary handles empty session."""
        from mara_host.benchmarks.mcu.perf_monitor import PerfSession

        session = PerfSession()
        summary = session.get_summary()

        assert summary == {}


# =============================================================================
# Telemetry Section Parser Tests
# =============================================================================


class TestTelemetryBenchmarkSection:
    """Tests for TELEM_BENCHMARK section parser."""

    def test_section_definition(self):
        """TELEM_BENCHMARK section has correct properties."""
        from mara_host.tools.schema.telemetry._benchmark import SECTION

        assert SECTION.name == "TELEM_BENCHMARK"
        assert SECTION.section_id == 0x13
        assert SECTION.variable_length is True
        assert SECTION.custom_parser is not None

    def test_parse_header_only(self):
        """Parser handles header-only payload."""
        from mara_host.tools.schema.telemetry._benchmark import parse_benchmark_section

        # 4-byte header: state=2, active_test=1, queue_depth=0, result_count=0
        body = bytes([2, 1, 0, 0])
        result = parse_benchmark_section(body, 12345)

        assert result is not None
        assert result["bench_state"] == 2
        assert result["active_test"] == 1
        assert result["state_name"] == "complete"
        assert "latest" not in result

    def test_parse_with_result(self):
        """Parser handles header + result payload."""
        from mara_host.tools.schema.telemetry._benchmark import parse_benchmark_section
        import struct

        # 4-byte header
        header = bytes([2, 0x30, 0, 1])  # complete, PID_STEP, 0 queued, 1 result

        # 56-byte BenchResult (packed)
        # Format: <BBBBI IIIIIIII HH III
        result_data = struct.pack(
            "<BBBBI IIIIIIII HH III",
            0x30,  # test_id
            2,  # state
            0,  # error
            0,  # reserved
            12345,  # timestamp_ms
            1000,  # mean_us
            500,  # min_us
            2000,  # max_us
            900,  # p50_us
            1500,  # p95_us
            1800,  # p99_us
            200,  # jitter_us
            100000,  # total_us
            100,  # samples
            0,  # budget_violations
            100050,  # extra1 (throughput * 100)
            0,  # extra2
            0,  # extra3
        )

        body = header + result_data
        result = parse_benchmark_section(body, 12345)

        assert result is not None
        assert result["bench_state"] == 2
        assert "latest" in result
        assert result["latest"]["test_id"] == 0x30
        assert result["latest"]["mean_us"] == 1000
        assert result["latest"]["throughput_hz"] == pytest.approx(1000.5, rel=0.01)

    def test_parse_too_short(self):
        """Parser returns None for too-short payload."""
        from mara_host.tools.schema.telemetry._benchmark import parse_benchmark_section

        body = bytes([1, 2])  # Only 2 bytes
        result = parse_benchmark_section(body, 12345)

        assert result is None


# =============================================================================
# Command Schema Tests
# =============================================================================


class TestBenchmarkCommands:
    """Tests for benchmark command definitions."""

    def test_commands_defined(self):
        """Verify all benchmark commands are defined."""
        from mara_host.tools.schema.commands._benchmark import BENCHMARK_COMMAND_OBJECTS

        expected_commands = [
            "CMD_BENCH_START",
            "CMD_BENCH_STOP",
            "CMD_BENCH_STATUS",
            "CMD_BENCH_LIST_TESTS",
            "CMD_BENCH_GET_RESULTS",
            "CMD_BENCH_RUN_BOOT_TESTS",
            "CMD_PERF_RESET",
        ]

        for cmd in expected_commands:
            assert cmd in BENCHMARK_COMMAND_OBJECTS, f"Missing command: {cmd}"

    def test_bench_start_payload(self):
        """CMD_BENCH_START has correct payload definition."""
        from mara_host.tools.schema.commands._benchmark import BENCHMARK_COMMAND_OBJECTS

        cmd = BENCHMARK_COMMAND_OBJECTS["CMD_BENCH_START"]
        assert cmd.kind == "cmd"
        assert cmd.direction == "host->mcu"
        assert "test_id" in cmd.payload
        assert "iterations" in cmd.payload
        assert cmd.payload["test_id"].required is True

    def test_legacy_export(self):
        """Legacy BENCHMARK_COMMANDS dict is exported."""
        from mara_host.tools.schema.commands._benchmark import BENCHMARK_COMMANDS

        assert "CMD_BENCH_START" in BENCHMARK_COMMANDS
        assert isinstance(BENCHMARK_COMMANDS["CMD_BENCH_START"], dict)
