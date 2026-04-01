# mara_host/services/testing/__init__.py
"""Testing services."""

from mara_host.services.testing.test_service import TestService, TestResult, TestStatus
from mara_host.services.testing.firmware_test_service import (
    FirmwareTestService,
    FirmwareTestResult,
)

__all__ = [
    # Robot self-tests
    "TestService",
    "TestResult",
    "TestStatus",
    # Firmware unit tests
    "FirmwareTestService",
    "FirmwareTestResult",
]
