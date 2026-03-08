# mara_host/services/testing/test_service.py
"""
Robot testing service.

Provides a clean interface for running robot self-tests,
independent of CLI concerns.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any

from mara_host.command.client import MaraClient


class TestStatus(Enum):
    """Test result status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: TestStatus
    message: str = ""
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)


class TestService:
    """
    Service for running robot self-tests.

    Example:
        async with TestService.create("/dev/ttyUSB0") as service:
            results = await service.run_all()
            for result in results:
                print(f"{result.name}: {result.status.value}")
    """

    def __init__(self, client: MaraClient):
        """
        Initialize test service with an existing client.

        Args:
            client: Connected MaraClient
        """
        self.client = client
        self._results: list[TestResult] = []

    @classmethod
    async def create(cls, port: str, baudrate: int = 115200) -> "TestService":
        """
        Create a test service and connect to the robot.

        Args:
            port: Serial port path
            baudrate: Baud rate

        Returns:
            Connected TestService instance
        """
        from mara_host.transport.serial_transport import SerialTransport

        transport = SerialTransport(port, baudrate=baudrate)
        client = MaraClient(transport, connection_timeout_s=6.0)
        await client.start()

        return cls(client)

    async def close(self) -> None:
        """Disconnect from the robot."""
        await self.client.stop()

    async def __aenter__(self) -> "TestService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # -------------------------------------------------------------------------
    # Test runners
    # -------------------------------------------------------------------------

    async def run_all(self) -> list[TestResult]:
        """Run all tests and return results."""
        self._results = []

        # Run tests in order
        self._results.append(await self.test_connection())
        self._results.append(await self.test_ping())
        self._results.append(await self.test_arm_disarm())
        self._results.append(await self.test_mode_switch())
        self._results.append(await self.test_led())
        self._results.append(await self.test_heartbeat())

        return self._results

    async def run_tests(self, test_names: list[str]) -> list[TestResult]:
        """Run specific tests by name."""
        self._results = []

        test_map = {
            "connection": self.test_connection,
            "ping": self.test_ping,
            "arm_disarm": self.test_arm_disarm,
            "mode": self.test_mode_switch,
            "led": self.test_led,
            "heartbeat": self.test_heartbeat,
            "motors": self.test_motors,
            "encoders": self.test_encoders,
            "servos": self.test_servos,
            "sensors": self.test_sensors,
            "gpio": self.test_gpio,
        }

        for name in test_names:
            if name in test_map:
                self._results.append(await test_map[name]())
            else:
                self._results.append(TestResult(
                    name=name,
                    status=TestStatus.SKIPPED,
                    message=f"Unknown test: {name}"
                ))

        return self._results

    # -------------------------------------------------------------------------
    # Individual tests
    # -------------------------------------------------------------------------

    async def test_connection(self) -> TestResult:
        """Test that we can connect to the robot."""
        start = time.time()
        try:
            # Connection already established if we got here
            duration = (time.time() - start) * 1000

            return TestResult(
                name="Connection",
                status=TestStatus.PASSED,
                message="Connected successfully",
                duration_ms=duration,
                details={
                    "firmware": self.client.firmware_version,
                    "protocol": self.client.protocol_version,
                    "features": self.client.features or [],
                }
            )
        except Exception as e:
            return TestResult(
                name="Connection",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_ping(self) -> TestResult:
        """Test ping/pong response."""
        start = time.time()
        try:
            pong_received = asyncio.Event()

            def on_pong(data):
                pong_received.set()

            self.client.bus.subscribe("pong", on_pong)
            await self.client.send_ping()

            await asyncio.wait_for(pong_received.wait(), timeout=2.0)
            duration = (time.time() - start) * 1000

            return TestResult(
                name="Ping/Pong",
                status=TestStatus.PASSED,
                message="Response received",
                duration_ms=duration
            )
        except asyncio.TimeoutError:
            return TestResult(
                name="Ping/Pong",
                status=TestStatus.FAILED,
                message="No pong received",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return TestResult(
                name="Ping/Pong",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_arm_disarm(self) -> TestResult:
        """Test arm and disarm state transitions."""
        start = time.time()
        try:
            # Ensure disarmed
            await self.client.cmd_disarm()
            await asyncio.sleep(0.05)

            # Arm
            await self.client.cmd_arm()
            await asyncio.sleep(0.05)

            # Disarm
            await self.client.cmd_disarm()
            await asyncio.sleep(0.05)

            duration = (time.time() - start) * 1000

            return TestResult(
                name="Arm/Disarm",
                status=TestStatus.PASSED,
                message="State transitions OK",
                duration_ms=duration
            )
        except Exception as e:
            return TestResult(
                name="Arm/Disarm",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_mode_switch(self) -> TestResult:
        """Test mode switching (IDLE -> ACTIVE -> IDLE)."""
        start = time.time()
        try:
            # Ensure we're in IDLE mode first
            await self.client.cmd_deactivate()
            await asyncio.sleep(0.05)

            # Switch to ACTIVE
            await self.client.cmd_activate()
            await asyncio.sleep(0.1)

            # Back to IDLE
            await self.client.cmd_deactivate()
            await asyncio.sleep(0.05)

            duration = (time.time() - start) * 1000

            return TestResult(
                name="Mode Switch",
                status=TestStatus.PASSED,
                message="IDLE -> ACTIVE -> IDLE OK",
                duration_ms=duration
            )
        except Exception as e:
            return TestResult(
                name="Mode Switch",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_led(self) -> TestResult:
        """Test LED on/off commands."""
        start = time.time()
        try:
            await self.client.cmd_led_on()
            await asyncio.sleep(0.1)
            await self.client.cmd_led_off()
            await asyncio.sleep(0.1)

            duration = (time.time() - start) * 1000

            return TestResult(
                name="LED Control",
                status=TestStatus.PASSED,
                message="On/Off commands sent",
                duration_ms=duration
            )
        except Exception as e:
            return TestResult(
                name="LED Control",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_heartbeat(self) -> TestResult:
        """Test heartbeat reception."""
        start = time.time()
        try:
            heartbeat_received = asyncio.Event()

            def on_heartbeat(data):
                heartbeat_received.set()

            self.client.bus.subscribe("heartbeat", on_heartbeat)

            await asyncio.wait_for(heartbeat_received.wait(), timeout=3.0)
            duration = (time.time() - start) * 1000

            return TestResult(
                name="Heartbeat",
                status=TestStatus.PASSED,
                message="Receiving heartbeats",
                duration_ms=duration
            )
        except asyncio.TimeoutError:
            return TestResult(
                name="Heartbeat",
                status=TestStatus.FAILED,
                message="No heartbeat received",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return TestResult(
                name="Heartbeat",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_motors(
        self,
        motor_ids: list[int] = None,
        confirm_callback: Callable[[], bool] = None
    ) -> TestResult:
        """
        Test motor control.

        Args:
            motor_ids: List of motor IDs to test (default: [0])
            confirm_callback: Optional callback to confirm before running motors.
                              Should return True to proceed.
        """
        if motor_ids is None:
            motor_ids = [0]

        start = time.time()
        try:
            # Confirm if callback provided
            if confirm_callback and not confirm_callback():
                return TestResult(
                    name="Motors",
                    status=TestStatus.SKIPPED,
                    message="User cancelled"
                )

            # Arm the robot first
            await self.client.cmd_arm()
            await asyncio.sleep(0.1)

            # Test each motor briefly
            for motor_id in motor_ids:
                await self.client.cmd_dc_motor_set(motor_id, 50)
                await asyncio.sleep(0.3)
                await self.client.cmd_dc_motor_set(motor_id, 0)
                await asyncio.sleep(0.1)

            # Disarm
            await self.client.cmd_disarm()

            duration = (time.time() - start) * 1000

            return TestResult(
                name="Motors",
                status=TestStatus.PASSED,
                message=f"Tested motors: {motor_ids}",
                duration_ms=duration
            )
        except Exception as e:
            # Ensure disarmed on error
            try:
                await self.client.cmd_disarm()
            except Exception:
                pass

            return TestResult(
                name="Motors",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_encoders(self, duration_s: float = 2.0) -> TestResult:
        """Test encoder feedback."""
        start = time.time()
        readings = []

        try:
            def on_encoder(data):
                readings.append(data)

            self.client.bus.subscribe("telemetry.encoder0", on_encoder)
            await asyncio.sleep(duration_s)

            if readings:
                return TestResult(
                    name="Encoders",
                    status=TestStatus.PASSED,
                    message=f"Received {len(readings)} readings",
                    duration_ms=(time.time() - start) * 1000,
                    details={"sample_count": len(readings)}
                )
            else:
                return TestResult(
                    name="Encoders",
                    status=TestStatus.FAILED,
                    message="No encoder data received",
                    duration_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return TestResult(
                name="Encoders",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_servos(self, servo_ids: list[int] = None) -> TestResult:
        """Test servo control with a small sweep."""
        if servo_ids is None:
            servo_ids = [0]

        start = time.time()
        try:
            for servo_id in servo_ids:
                # Attach servo - use servo_id as channel (default mapping)
                # min_us=500, max_us=2500 for wider range
                await self.client.cmd_servo_attach(
                    servo_id=servo_id,
                    channel=servo_id,  # Map servo_id to same channel
                    min_us=500,
                    max_us=2500
                )
                await asyncio.sleep(0.1)

                # Small sweep: 90 -> 45 -> 135 -> 90
                for angle in [90, 45, 135, 90]:
                    await self.client.cmd_servo_set_angle(servo_id, float(angle))
                    await asyncio.sleep(0.3)

                # Detach
                await self.client.cmd_servo_detach(servo_id)

            duration = (time.time() - start) * 1000

            return TestResult(
                name="Servos",
                status=TestStatus.PASSED,
                message=f"Tested servos: {servo_ids}",
                duration_ms=duration
            )
        except Exception as e:
            return TestResult(
                name="Servos",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_sensors(self, duration_s: float = 2.0) -> TestResult:
        """Test sensor data collection."""
        start = time.time()
        imu_data = []
        ultrasonic_data = []

        try:
            def on_imu(data):
                imu_data.append(data)

            def on_ultrasonic(data):
                ultrasonic_data.append(data)

            self.client.bus.subscribe("telemetry.imu", on_imu)
            self.client.bus.subscribe("telemetry.ultrasonic", on_ultrasonic)

            await asyncio.sleep(duration_s)

            details = {
                "imu_samples": len(imu_data),
                "ultrasonic_samples": len(ultrasonic_data),
            }

            if imu_data or ultrasonic_data:
                return TestResult(
                    name="Sensors",
                    status=TestStatus.PASSED,
                    message=f"IMU: {len(imu_data)}, Ultrasonic: {len(ultrasonic_data)}",
                    duration_ms=(time.time() - start) * 1000,
                    details=details
                )
            else:
                return TestResult(
                    name="Sensors",
                    status=TestStatus.FAILED,
                    message="No sensor data received",
                    duration_ms=(time.time() - start) * 1000,
                    details=details
                )
        except Exception as e:
            return TestResult(
                name="Sensors",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def test_gpio(self, pin: int = 2) -> TestResult:
        """Test GPIO read/write on a pin."""
        start = time.time()
        try:
            # Set as output
            await self.client.cmd_gpio_mode(pin, "output")
            await asyncio.sleep(0.05)

            # Toggle
            await self.client.cmd_gpio_write(pin, True)
            await asyncio.sleep(0.1)
            await self.client.cmd_gpio_write(pin, False)
            await asyncio.sleep(0.1)

            duration = (time.time() - start) * 1000

            return TestResult(
                name="GPIO",
                status=TestStatus.PASSED,
                message=f"Toggled GPIO {pin}",
                duration_ms=duration
            )
        except Exception as e:
            return TestResult(
                name="GPIO",
                status=TestStatus.FAILED,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    # -------------------------------------------------------------------------
    # Results access
    # -------------------------------------------------------------------------

    @property
    def results(self) -> list[TestResult]:
        """Get all test results from the last run."""
        return self._results.copy()

    @property
    def passed_count(self) -> int:
        """Count of passed tests."""
        return sum(1 for r in self._results if r.status == TestStatus.PASSED)

    @property
    def failed_count(self) -> int:
        """Count of failed tests."""
        return sum(1 for r in self._results if r.status == TestStatus.FAILED)

    @property
    def all_passed(self) -> bool:
        """True if all tests passed."""
        return self.failed_count == 0 and self.passed_count > 0
