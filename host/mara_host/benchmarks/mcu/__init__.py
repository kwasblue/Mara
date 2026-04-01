# mara_host/benchmarks/mcu/__init__.py
"""
MCU benchmark integration module.

Provides tools for:
- Triggering benchmarks on the MCU via commands
- Collecting results from MCU telemetry
- Monitoring TELEM_PERF metrics
- Test catalog with ID-to-name mapping

## Quick Start

```python
from mara_host.benchmarks.mcu import TriggeredBenchmark, PerfMonitor

# Run a triggered benchmark
async with TriggeredBenchmark(transport) as bench:
    result = await bench.run_test(TestId.LOOP_TIMING, iterations=100)
    print(result)

# Monitor MCU performance
async with PerfMonitor(transport) as monitor:
    metrics = await monitor.get_perf()
    print(f"Loop time: {metrics['avg_total_us']}us")
```
"""

from mara_host.benchmarks.mcu.test_catalog import (
    TestId,
    BenchState,
    BenchError,
    TEST_CATALOG,
    get_test_name,
    get_test_description,
)

from mara_host.benchmarks.mcu.triggered_benchmark import (
    TriggeredBenchmark,
    MCUBenchmarkResult,
)

from mara_host.benchmarks.mcu.perf_monitor import (
    PerfMonitor,
    PerfMetrics,
)


__all__ = [
    # Test catalog
    "TestId",
    "BenchState",
    "BenchError",
    "TEST_CATALOG",
    "get_test_name",
    "get_test_description",
    # Triggered benchmarks
    "TriggeredBenchmark",
    "MCUBenchmarkResult",
    # Performance monitoring
    "PerfMonitor",
    "PerfMetrics",
]
