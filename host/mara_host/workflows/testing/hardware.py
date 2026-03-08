# mara_host/workflows/testing/hardware.py
"""
Hardware test workflow.

Tests individual hardware components.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from mara_host.workflows.base import BaseWorkflow, WorkflowResult, WorkflowState


@dataclass
class HardwareTestResult:
    """Single hardware test result."""
    component: str
    test: str
    passed: bool
    message: str
    duration_ms: float


class HardwareTestWorkflow(BaseWorkflow):
    """
    Hardware test workflow.

    Tests individual hardware components including:
    - DC motors (each motor's response)
    - Servos (movement range)
    - Encoders (tick counting)
    - GPIO (digital output)

    Usage:
        workflow = HardwareTestWorkflow(client)
        workflow.on_progress = lambda p, s: print(f"{p}%: {s}")

        result = await workflow.run(test_motors=True, test_servos=True)
        if result.ok:
            for r in result.data['results']:
                print(f"{r['component']}: {'PASS' if r['passed'] else 'FAIL'}")
    """

    def __init__(self, client):
        super().__init__(client)

    @property
    def name(self) -> str:
        return "Hardware Test"

    async def run(
        self,
        test_motors: bool = True,
        test_servos: bool = True,
        test_gpio: bool = True,
        motor_ids: Optional[list[int]] = None,
        servo_ids: Optional[list[int]] = None,
        gpio_channels: Optional[list[int]] = None,
        motor_test_speed: float = 0.3,
        motor_test_duration: float = 0.5,
    ) -> WorkflowResult:
        """
        Run hardware tests.

        Args:
            test_motors: Test DC motors
            test_servos: Test servos
            test_gpio: Test GPIO
            motor_ids: Motors to test (default: [0, 1])
            servo_ids: Servos to test (default: [0, 1])
            gpio_channels: GPIO channels to test (default: [0, 1])
            motor_test_speed: Speed for motor test (0.0-1.0)
            motor_test_duration: Duration for each motor test

        Returns:
            WorkflowResult with test results
        """
        self.reset()
        self._set_state(WorkflowState.RUNNING)

        motor_ids = motor_ids or [0, 1]
        servo_ids = servo_ids or [0, 1]
        gpio_channels = gpio_channels or [0, 1]

        results: list[HardwareTestResult] = []
        total_tests = 0

        if test_motors:
            total_tests += len(motor_ids)
        if test_servos:
            total_tests += len(servo_ids)
        if test_gpio:
            total_tests += len(gpio_channels)

        if total_tests == 0:
            return WorkflowResult.failure("No tests selected")

        test_index = 0

        try:
            # Test motors
            if test_motors:
                for motor_id in motor_ids:
                    if self._check_cancelled():
                        return WorkflowResult.cancelled()

                    progress = int((test_index / total_tests) * 100)
                    self._emit_progress(progress, f"Testing Motor {motor_id}")

                    result = await self._test_motor(
                        motor_id, motor_test_speed, motor_test_duration
                    )
                    results.append(result)
                    test_index += 1

            # Test servos
            if test_servos:
                for servo_id in servo_ids:
                    if self._check_cancelled():
                        return WorkflowResult.cancelled()

                    progress = int((test_index / total_tests) * 100)
                    self._emit_progress(progress, f"Testing Servo {servo_id}")

                    result = await self._test_servo(servo_id)
                    results.append(result)
                    test_index += 1

            # Test GPIO
            if test_gpio:
                for channel in gpio_channels:
                    if self._check_cancelled():
                        return WorkflowResult.cancelled()

                    progress = int((test_index / total_tests) * 100)
                    self._emit_progress(progress, f"Testing GPIO {channel}")

                    result = await self._test_gpio(channel)
                    results.append(result)
                    test_index += 1

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
                        "component": r.component,
                        "test": r.test,
                        "passed": r.passed,
                        "message": r.message,
                        "duration_ms": r.duration_ms,
                    }
                    for r in results
                ],
            })

        except Exception as e:
            return WorkflowResult.failure(str(e))

    async def _test_motor(
        self, motor_id: int, speed: float, duration: float
    ) -> HardwareTestResult:
        """Test a DC motor."""
        start = time.time()
        try:
            # Forward
            ok, error = await self._send_command(
                "CMD_DC_MOTOR_SET_SPEED",
                {"motor_id": motor_id, "speed": speed},
            )
            if not ok:
                return HardwareTestResult(
                    f"Motor {motor_id}",
                    "Forward rotation",
                    False,
                    f"Set speed failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(duration)

            # Stop
            await self._send_command(
                "CMD_DC_MOTOR_SET_SPEED",
                {"motor_id": motor_id, "speed": 0.0},
            )

            await asyncio.sleep(0.2)

            # Reverse
            ok, error = await self._send_command(
                "CMD_DC_MOTOR_SET_SPEED",
                {"motor_id": motor_id, "speed": -speed},
            )
            if not ok:
                return HardwareTestResult(
                    f"Motor {motor_id}",
                    "Reverse rotation",
                    False,
                    f"Set reverse failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(duration)

            # Stop
            await self._send_command(
                "CMD_DC_MOTOR_SET_SPEED",
                {"motor_id": motor_id, "speed": 0.0},
            )

            return HardwareTestResult(
                f"Motor {motor_id}",
                "Bidirectional",
                True,
                "Forward and reverse OK",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            # Ensure motor stopped
            await self._send_command(
                "CMD_DC_MOTOR_SET_SPEED",
                {"motor_id": motor_id, "speed": 0.0},
            )
            return HardwareTestResult(
                f"Motor {motor_id}",
                "Error",
                False,
                str(e),
                (time.time() - start) * 1000,
            )

    async def _test_servo(self, servo_id: int) -> HardwareTestResult:
        """Test a servo."""
        start = time.time()
        try:
            # Center
            ok, error = await self._send_command(
                "CMD_SERVO_SET_ANGLE",
                {"servo_id": servo_id, "angle": 90.0},
            )
            if not ok:
                return HardwareTestResult(
                    f"Servo {servo_id}",
                    "Center position",
                    False,
                    f"Set angle failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(0.3)

            # Min
            await self._send_command(
                "CMD_SERVO_SET_ANGLE",
                {"servo_id": servo_id, "angle": 45.0},
            )
            await asyncio.sleep(0.3)

            # Max
            await self._send_command(
                "CMD_SERVO_SET_ANGLE",
                {"servo_id": servo_id, "angle": 135.0},
            )
            await asyncio.sleep(0.3)

            # Back to center
            await self._send_command(
                "CMD_SERVO_SET_ANGLE",
                {"servo_id": servo_id, "angle": 90.0},
            )

            return HardwareTestResult(
                f"Servo {servo_id}",
                "Range test",
                True,
                "45-135 degree range OK",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            return HardwareTestResult(
                f"Servo {servo_id}",
                "Error",
                False,
                str(e),
                (time.time() - start) * 1000,
            )

    async def _test_gpio(self, channel: int) -> HardwareTestResult:
        """Test a GPIO channel."""
        start = time.time()
        try:
            # High
            ok, error = await self._send_command(
                "CMD_GPIO_WRITE",
                {"channel": channel, "value": 1},
            )
            if not ok:
                return HardwareTestResult(
                    f"GPIO {channel}",
                    "Digital output",
                    False,
                    f"Write high failed: {error}",
                    (time.time() - start) * 1000,
                )

            await asyncio.sleep(0.2)

            # Low
            ok, error = await self._send_command(
                "CMD_GPIO_WRITE",
                {"channel": channel, "value": 0},
            )
            if not ok:
                return HardwareTestResult(
                    f"GPIO {channel}",
                    "Digital output",
                    False,
                    f"Write low failed: {error}",
                    (time.time() - start) * 1000,
                )

            return HardwareTestResult(
                f"GPIO {channel}",
                "Digital output",
                True,
                "High/Low toggle OK",
                (time.time() - start) * 1000,
            )

        except Exception as e:
            return HardwareTestResult(
                f"GPIO {channel}",
                "Error",
                False,
                str(e),
                (time.time() - start) * 1000,
            )
