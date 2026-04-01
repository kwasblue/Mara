# mara_host/benchmarks/mcu/test_catalog.py
"""
MCU benchmark test catalog.

Maps test IDs to human-readable names and descriptions.
This should be kept in sync with firmware/mcu/include/benchmark/BenchmarkTypes.h
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional


class TestId(IntEnum):
    """Benchmark test identifiers matching MCU BenchmarkTypes.h."""

    # Core timing tests (0x01-0x0F)
    LOOP_TIMING = 0x01
    SIGNAL_BUS_LATENCY = 0x02
    INTENT_CONSUME = 0x03
    EVENT_BUS_PUBLISH = 0x04

    # Command/comms tests (0x20-0x2F)
    PING_INTERNAL = 0x20
    CMD_DECODE = 0x21
    TELEM_ENCODE = 0x22
    TELEM_JSON_ENCODE = 0x23

    # Control subsystem tests (0x30-0x3F)
    PID_STEP = 0x30
    OBSERVER_UPDATE = 0x31
    KERNEL_STEP = 0x32
    MOTION_UPDATE = 0x33

    # Memory/allocation tests (0x40-0x4F)
    HEAP_ALLOC_SMALL = 0x40
    HEAP_ALLOC_MEDIUM = 0x41

    # Custom/user tests (0x80-0xFF)
    USER_TEST_0 = 0x80
    USER_TEST_1 = 0x81
    USER_TEST_2 = 0x82
    USER_TEST_3 = 0x83

    UNKNOWN = 0xFF


class BenchState(IntEnum):
    """Benchmark system state."""

    IDLE = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3
    QUEUED = 4


class BenchError(IntEnum):
    """Benchmark error codes."""

    NONE = 0
    UNKNOWN_TEST = 1
    QUEUE_FULL = 2
    TIMEOUT = 3
    BUDGET_EXCEEDED = 4
    RT_VIOLATION = 5
    CANCELLED = 6
    NOT_AVAILABLE = 7


@dataclass(frozen=True)
class TestInfo:
    """Information about a benchmark test."""

    id: TestId
    name: str
    description: str
    rt_safe: bool = False
    boot_test: bool = False


# Static test catalog (fallback when MCU not connected)
TEST_CATALOG: Dict[TestId, TestInfo] = {
    TestId.LOOP_TIMING: TestInfo(
        id=TestId.LOOP_TIMING,
        name="LOOP_TIMING",
        description="Empty loop iteration overhead",
        rt_safe=True,
        boot_test=True,
    ),
    TestId.SIGNAL_BUS_LATENCY: TestInfo(
        id=TestId.SIGNAL_BUS_LATENCY,
        name="SIGNAL_BUS",
        description="SignalBus get/set latency",
        rt_safe=True,
        boot_test=True,
    ),
    TestId.INTENT_CONSUME: TestInfo(
        id=TestId.INTENT_CONSUME,
        name="INTENT_CONSUME",
        description="IntentBuffer consume time",
        rt_safe=True,
    ),
    TestId.EVENT_BUS_PUBLISH: TestInfo(
        id=TestId.EVENT_BUS_PUBLISH,
        name="EVENT_BUS",
        description="EventBus publish latency",
        rt_safe=True,
    ),
    TestId.PING_INTERNAL: TestInfo(
        id=TestId.PING_INTERNAL,
        name="PING_INTERNAL",
        description="Internal ping processing",
        rt_safe=True,
        boot_test=True,
    ),
    TestId.CMD_DECODE: TestInfo(
        id=TestId.CMD_DECODE,
        name="CMD_DECODE",
        description="JSON command decode time",
        rt_safe=False,
    ),
    TestId.TELEM_ENCODE: TestInfo(
        id=TestId.TELEM_ENCODE,
        name="TELEM_ENCODE",
        description="Binary telemetry encode",
        rt_safe=True,
    ),
    TestId.TELEM_JSON_ENCODE: TestInfo(
        id=TestId.TELEM_JSON_ENCODE,
        name="TELEM_JSON",
        description="JSON telemetry encode",
        rt_safe=False,
    ),
    TestId.PID_STEP: TestInfo(
        id=TestId.PID_STEP,
        name="PID_STEP",
        description="PID controller step()",
        rt_safe=True,
    ),
    TestId.OBSERVER_UPDATE: TestInfo(
        id=TestId.OBSERVER_UPDATE,
        name="OBSERVER",
        description="Observer update()",
        rt_safe=True,
    ),
    TestId.KERNEL_STEP: TestInfo(
        id=TestId.KERNEL_STEP,
        name="KERNEL_STEP",
        description="Full ControlKernel step",
        rt_safe=True,
    ),
    TestId.MOTION_UPDATE: TestInfo(
        id=TestId.MOTION_UPDATE,
        name="MOTION_UPDATE",
        description="MotionController update",
        rt_safe=True,
    ),
    TestId.HEAP_ALLOC_SMALL: TestInfo(
        id=TestId.HEAP_ALLOC_SMALL,
        name="HEAP_64B",
        description="64-byte heap alloc/free",
        rt_safe=False,
    ),
    TestId.HEAP_ALLOC_MEDIUM: TestInfo(
        id=TestId.HEAP_ALLOC_MEDIUM,
        name="HEAP_512B",
        description="512-byte heap alloc/free",
        rt_safe=False,
    ),
}


def get_test_name(test_id: int) -> str:
    """Get test name from ID."""
    try:
        tid = TestId(test_id)
        if tid in TEST_CATALOG:
            return TEST_CATALOG[tid].name
    except ValueError:
        pass
    return f"TEST_0x{test_id:02X}"


def get_test_description(test_id: int) -> Optional[str]:
    """Get test description from ID."""
    try:
        tid = TestId(test_id)
        if tid in TEST_CATALOG:
            return TEST_CATALOG[tid].description
    except ValueError:
        pass
    return None
