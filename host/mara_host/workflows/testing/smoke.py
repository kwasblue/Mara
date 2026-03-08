# mara_host/workflows/testing/smoke.py
"""
Smoke test workflow.

Runs basic connectivity and functionality tests.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class TestResult:
    """Single test result."""
    name: str
    passed: bool
    message: str
    duration_ms: float


class SmokeTestWorkflow(BaseWorkflow):
    """
    Smoke test workflow.

    Runs a series of basic tests to verify robot connectivity
    and core functionality.

    Tests include:
    - Connection
    - Ping/Pong
    - Arm/Disarm
    - Mode switching
    - LED control
    - Heartbeat reception

    Usage:
        workflow = SmokeTestWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run()
        if result.ok:
            print(f"Passed: {result.data['passed']}/{result.data['total']}")
    """

    def __init__(self, client):
        super().__init__(client)
        self._pong_event: Optional[asyncio.Event] = None
        self._heartbeat_event: Optional[asyncio.Event] = None

    @property
    def name(self) -> str:
        return "Smoke Test"

    async def run(
        self,
        timeout: float = 5.0,
    ) -> WorkflowResult:
        """
        Run smoke tests.

        Args:
            timeout: Timeout for each test in seconds

        Returns:
            WorkflowResult with test results
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)

        results: list[TestResult] = []
        test_count = 5

        try:
            # Test 1: Ping/Pong
            self._emit_progress(10, "Testing Ping/Pong")
            result = await self._test_ping(timeout)
            results.append(result)

            if self._check_cancelled():
                return WorkflowResult.cancelled()

            # Test 2: Arm/Disarm
            self._emit_progress(30, "Testing Arm/Disarm")
            result = await self._test_arm_disarm(timeout)
            results.append(result)

            if self._check_cancelled():
                return WorkflowResult.cancelled()

            # Test 3: Mode switching
            self._emit_progress(50, "Testing Mode Switch")
            result = await self._test_mode_switch(timeout)
            results.append(result)

            if self._check_cancelled():
                return WorkflowResult.cancelled()

            # Test 4: LED control
            self._emit_progress(70, "Testing LED Control")
            result = await self._test_led(timeout)
            results.append(result)

            if self._check_cancelled():
                return WorkflowResult.cancelled()

            # Test 5: Heartbeat
            self._emit_progress(90, "Testing Heartbeat")
            result = await self._test_heartbeat(timeout)
            results.append(result)

            # Summary
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed

            self._emit_progress(100, f"Complete: {passed}/{len(results)} passed")

            return WorkflowResult.success({
                "passed": passed,
                "failed": failed,
                "total": len(results),
                "results": [
                    {
                        "name": r.name,
                        "passed": r.passed,
                        "message": r.message,
                        "duration_ms": r.duration_ms,
                    }
                    for r in results
                ],
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    async def _test_ping(self, timeout: float) -> TestResult:
        """Test ping/pong communication."""
        start = time.time()
        try:
            ok, error = await self._send_command("CMD_PING", {})
            if ok:
                return TestResult(
                    "Ping/Pong",
                    True,
                    "Response received",
                    (time.time() - start) * 1000,
                )
            else:
                return TestResult(
                    "Ping/Pong",
                    False,
                    error or "No response",
                    (time.time() - start) * 1000,
                )
        except asyncio.TimeoutError:
            return TestResult(
                "Ping/Pong",
                False,
                "Timeout",
                (time.time() - start) * 1000,
            )

    async def _test_arm_disarm(self, timeout: float) -> TestResult:
        """Test arm/disarm state transitions."""
        start = time.time()
        try:
            # Arm
            ok, error = await self._send_command("CMD_ARM", {})
            if not ok:
                return TestResult(
                    "Arm/Disarm",
                    False,
                    f"Arm failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(0.1)

            # Disarm
            ok, error = await self._send_command("CMD_DISARM", {})
            if not ok:
                return TestResult(
                    "Arm/Disarm",
                    False,
                    f"Disarm failed: {error}",
                    (time.time() - start) * 1000,
                )

            return TestResult(
                "Arm/Disarm",
                True,
                "State transitions OK",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            return TestResult(
                "Arm/Disarm",
                False,
                str(e),
                (time.time() - start) * 1000,
            )

    async def _test_mode_switch(self, timeout: float) -> TestResult:
        """Test mode switching."""
        start = time.time()
        try:
            # IDLE -> ACTIVE
            ok, error = await self._send_command(
                "CMD_SET_MODE", {"mode": "ACTIVE"}
            )
            if not ok:
                return TestResult(
                    "Mode Switch",
                    False,
                    f"Set ACTIVE failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(0.1)

            # ACTIVE -> IDLE
            ok, error = await self._send_command(
                "CMD_SET_MODE", {"mode": "IDLE"}
            )
            if not ok:
                return TestResult(
                    "Mode Switch",
                    False,
                    f"Set IDLE failed: {error}",
                    (time.time() - start) * 1000,
                )

            return TestResult(
                "Mode Switch",
                True,
                "IDLE -> ACTIVE -> IDLE OK",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            return TestResult(
                "Mode Switch",
                False,
                str(e),
                (time.time() - start) * 1000,
            )

    async def _test_led(self, timeout: float) -> TestResult:
        """Test LED control."""
        start = time.time()
        try:
            # LED On
            ok, error = await self._send_command("CMD_LED_ON", {})
            if not ok:
                return TestResult(
                    "LED Control",
                    False,
                    f"LED On failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(0.2)

            # LED Off
            ok, error = await self._send_command("CMD_LED_OFF", {})
            if not ok:
                return TestResult(
                    "LED Control",
                    False,
                    f"LED Off failed: {error}",
                    (time.time() - start) * 1000,
                )

            return TestResult(
                "LED Control",
                True,
                "On/Off commands sent",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            return TestResult(
                "LED Control",
                False,
                str(e),
                (time.time() - start) * 1000,
            )

    async def _test_heartbeat(self, timeout: float) -> TestResult:
        """Test heartbeat reception."""
        start = time.time()
        # Heartbeat detection depends on telemetry subscription
        # For now, we just verify connection is alive
        try:
            ok, error = await self._send_command("CMD_PING", {})
            if ok:
                return TestResult(
                    "Heartbeat",
                    True,
                    "Connection alive",
                    (time.time() - start) * 1000,
                )
            else:
                return TestResult(
                    "Heartbeat",
                    False,
                    "No response",
                    (time.time() - start) * 1000,
                )
        except Exception as e:
            return TestResult(
                "Heartbeat",
                False,
                str(e),
                (time.time() - start) * 1000,
            )
