# mara_host/benchmarks/__init__.py
"""
Performance benchmarks for the MARA platform.

This module provides a comprehensive benchmarking apparatus for measuring
performance across all platform layers:

- **Micro**: Measure one subsystem only (software overhead)
- **Integration**: Measure host-to-MCU path (protocol/transport overhead)
- **End-to-end**: Measure real behavior (actual robot responsiveness)

## Structure

```
benchmarks/
├── core.py              # Shared result types, timing utilities
├── commands/            # Command path benchmarks
│   ├── ping_rtt.py      # Basic ping round-trip
│   ├── command_rtt.py   # Full command latency breakdown
│   └── send_all/        # Comprehensive command validation
├── transport/           # Transport comparison benchmarks
│   ├── serial_bench.py  # Serial baseline
│   ├── tcp_bench.py     # TCP/WiFi baseline
│   └── compare.py       # Side-by-side comparison
├── serialization/       # Encode/decode benchmarks
│   ├── json_bench.py    # JSON encoding
│   ├── binary_bench.py  # Binary encoding
│   └── compare.py       # JSON vs binary comparison
├── streaming/           # CommandStreamer benchmarks
│   └── sustained_stream.py  # Sustained load testing
├── camera/              # Camera pipeline benchmarks
│   └── frame_latency.py # Frame fetch/decode timing
├── e2e/                 # End-to-end behavior benchmarks
│   ├── motor_response.py    # Command to telemetry change
│   └── servo_completion.py  # Servo movement completion
├── reports/             # JSON results storage
├── efficiency_eval.py   # Software efficiency benchmarks
└── latency/             # Legacy latency benchmarks
```

## Quick Start

Run ping benchmark:
```bash
python -m mara_host.benchmarks.commands.ping_rtt --port /dev/tty.usbserial
```

Run serialization comparison:
```bash
python -m mara_host.benchmarks.serialization.compare --iterations 1000
```

Run transport comparison:
```bash
python -m mara_host.benchmarks.transport.compare \\
    --serial /dev/tty.usbserial \\
    --tcp 192.168.4.1:3333
```

## Output Format

All benchmarks produce JSON reports saved to `reports/`:

```json
{
  "benchmark": "ping_rtt",
  "environment": {
    "transport": "serial",
    "port": "/dev/tty.usbserial",
    "baud_rate": 115200,
    "protocol": "json",
    "git_sha": "abc1234",
    "timestamp": "2026-04-01T10:30:00Z"
  },
  "results": {
    "mean_ms": 12.4,
    "p50_ms": 11.8,
    "p95_ms": 18.2,
    "p99_ms": 24.1,
    "min_ms": 8.1,
    "max_ms": 45.3,
    "jitter_ms": 3.2,
    "samples": 500,
    "error_count": 0,
    "retry_count": 2
  }
}
```
"""

from mara_host.benchmarks.core import (
    BenchmarkResult,
    BenchmarkEnvironment,
    BenchmarkReport,
    make_result,
    compute_stats,
    Timer,
    timed_loop,
    async_timed_loop,
    print_header,
    print_section,
    print_result,
    REPORTS_DIR,
)

__all__ = [
    # Result types
    "BenchmarkResult",
    "BenchmarkEnvironment",
    "BenchmarkReport",
    # Utilities
    "make_result",
    "compute_stats",
    "Timer",
    "timed_loop",
    "async_timed_loop",
    # Output
    "print_header",
    "print_section",
    "print_result",
    # Paths
    "REPORTS_DIR",
]
