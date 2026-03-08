# mara_host/api/testing.py
"""
Testing Framework API.

Provides programmatic access to hardware tests for validation
and diagnostics.

Example:
    async with Robot("/dev/ttyUSB0") as robot:
        # Run individual tests
        result = await robot.test.connection()
        print(f"Connection: {result.passed}")

        result = await robot.test.motors()
        print(f"Motors: {result.passed}")

        # Run all tests
        results = await robot.test.all()
        for name, result in results.items():
            print(f"{name}: {'PASS' if result.passed else 'FAIL'}")
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Dict, Callable, Any
from datetime import datetime
from enum import Enum
import asyncio

if TYPE_CHECKING:
    from mara_host.robot import Robot


class TestStatus(Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: TestStatus
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    results: List[TestResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return sum(r.duration_ms for r in self.results)


class Testing:
    """
    Hardware testing framework.

    Provides tests for:
    - Connection: Ping/handshake
    - Motors: DC motor movement
    - Servos: Servo sweep
    - GPIO: Digital I/O
    - Encoders: Count verification
    - Sensors: Reading validation
    - Latency: Round-trip timing

    Usage:
        test = robot.test
        result = await test.motors()
        if result.passed:
            print("Motors OK")
    """

    def __init__(self, robot: "Robot") -> None:
        self._robot = robot

    async def connection(self, timeout_ms: float = 1000) -> TestResult:
        """
        Test connection with ping.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            TestResult
        """
        start = datetime.now()
        try:
            ok, error = await asyncio.wait_for(
                self._robot.client.send_reliable("CMD_HEARTBEAT", {}),
                timeout=timeout_ms / 1000
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if ok:
                return TestResult(
                    name="connection",
                    status=TestStatus.PASSED,
                    message=f"Ping OK ({duration:.1f}ms)",
                    duration_ms=duration,
                )
            else:
                return TestResult(
                    name="connection",
                    status=TestStatus.FAILED,
                    message=f"Ping failed: {error}",
                    duration_ms=duration,
                )
        except asyncio.TimeoutError:
            return TestResult(
                name="connection",
                status=TestStatus.FAILED,
                message=f"Timeout after {timeout_ms}ms",
                duration_ms=timeout_ms,
            )
        except Exception as e:
            return TestResult(
                name="connection",
                status=TestStatus.ERROR,
                message=str(e),
            )

    async def motors(self, motor_ids: Optional[List[int]] = None) -> TestResult:
        """
        Test DC motors by running briefly.

        Args:
            motor_ids: Motor IDs to test (default: [0, 1])

        Returns:
            TestResult
        """
        if motor_ids is None:
            motor_ids = [0, 1]

        start = datetime.now()
        errors = []

        for motor_id in motor_ids:
            try:
                # Brief forward pulse
                ok, _ = await self._robot.client.send_reliable(
                    "CMD_DC_SET_SPEED",
                    {"motor_id": motor_id, "speed": 0.3}
                )
                if not ok:
                    errors.append(f"Motor {motor_id} set failed")
                    continue

                await asyncio.sleep(0.2)

                # Stop
                await self._robot.client.send_reliable(
                    "CMD_DC_STOP",
                    {"motor_id": motor_id}
                )
            except Exception as e:
                errors.append(f"Motor {motor_id}: {e}")

        duration = (datetime.now() - start).total_seconds() * 1000

        if errors:
            return TestResult(
                name="motors",
                status=TestStatus.FAILED,
                message="; ".join(errors),
                duration_ms=duration,
                details={"motor_ids": motor_ids},
            )

        return TestResult(
            name="motors",
            status=TestStatus.PASSED,
            message=f"Motors {motor_ids} OK",
            duration_ms=duration,
            details={"motor_ids": motor_ids},
        )

    async def servos(self, servo_ids: Optional[List[int]] = None) -> TestResult:
        """
        Test servos by sweeping to center.

        Args:
            servo_ids: Servo IDs to test (default: [0, 1])

        Returns:
            TestResult
        """
        if servo_ids is None:
            servo_ids = [0, 1]

        start = datetime.now()
        errors = []

        for servo_id in servo_ids:
            try:
                # Move to center
                ok, _ = await self._robot.client.send_reliable(
                    "CMD_SERVO_SET_ANGLE",
                    {"servo_id": servo_id, "angle": 90, "duration_ms": 300}
                )
                if not ok:
                    errors.append(f"Servo {servo_id} set failed")
            except Exception as e:
                errors.append(f"Servo {servo_id}: {e}")

        await asyncio.sleep(0.3)
        duration = (datetime.now() - start).total_seconds() * 1000

        if errors:
            return TestResult(
                name="servos",
                status=TestStatus.FAILED,
                message="; ".join(errors),
                duration_ms=duration,
            )

        return TestResult(
            name="servos",
            status=TestStatus.PASSED,
            message=f"Servos {servo_ids} centered",
            duration_ms=duration,
        )

    async def gpio(self, channel: int = 0) -> TestResult:
        """
        Test GPIO by toggling.

        Args:
            channel: GPIO channel to test

        Returns:
            TestResult
        """
        start = datetime.now()

        try:
            # High
            ok1, _ = await self._robot.client.send_reliable(
                "CMD_GPIO_WRITE",
                {"channel": channel, "value": 1}
            )
            await asyncio.sleep(0.1)

            # Low
            ok2, _ = await self._robot.client.send_reliable(
                "CMD_GPIO_WRITE",
                {"channel": channel, "value": 0}
            )

            duration = (datetime.now() - start).total_seconds() * 1000

            if ok1 and ok2:
                return TestResult(
                    name="gpio",
                    status=TestStatus.PASSED,
                    message=f"GPIO {channel} toggle OK",
                    duration_ms=duration,
                )
            else:
                return TestResult(
                    name="gpio",
                    status=TestStatus.FAILED,
                    message=f"GPIO {channel} write failed",
                    duration_ms=duration,
                )
        except Exception as e:
            return TestResult(
                name="gpio",
                status=TestStatus.ERROR,
                message=str(e),
            )

    async def latency(self, samples: int = 10) -> TestResult:
        """
        Measure command round-trip latency.

        Args:
            samples: Number of samples to take

        Returns:
            TestResult with latency statistics
        """
        latencies = []

        for _ in range(samples):
            start = datetime.now()
            try:
                await self._robot.client.send_reliable("CMD_HEARTBEAT", {})
                latency = (datetime.now() - start).total_seconds() * 1000
                latencies.append(latency)
            except Exception:
                pass

        if not latencies:
            return TestResult(
                name="latency",
                status=TestStatus.FAILED,
                message="No successful pings",
            )

        avg = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)

        return TestResult(
            name="latency",
            status=TestStatus.PASSED,
            message=f"Avg: {avg:.1f}ms (min: {min_lat:.1f}, max: {max_lat:.1f})",
            duration_ms=sum(latencies),
            details={
                "avg_ms": avg,
                "min_ms": min_lat,
                "max_ms": max_lat,
                "samples": len(latencies),
            },
        )

    async def all(self) -> Dict[str, TestResult]:
        """
        Run all tests.

        Returns:
            Dictionary of test name to TestResult
        """
        results = {}

        results["connection"] = await self.connection()
        if results["connection"].passed:
            results["motors"] = await self.motors()
            results["servos"] = await self.servos()
            results["gpio"] = await self.gpio()
            results["latency"] = await self.latency()

        return results

    async def run_suite(self, tests: Optional[List[str]] = None) -> TestSuite:
        """
        Run a test suite.

        Args:
            tests: List of test names, or None for all

        Returns:
            TestSuite with results
        """
        suite = TestSuite(name="hardware_tests")
        suite.start_time = datetime.now()

        test_map = {
            "connection": self.connection,
            "motors": self.motors,
            "servos": self.servos,
            "gpio": self.gpio,
            "latency": self.latency,
        }

        if tests is None:
            tests = list(test_map.keys())

        for test_name in tests:
            if test_name in test_map:
                result = await test_map[test_name]()
                suite.results.append(result)

        suite.end_time = datetime.now()
        return suite
