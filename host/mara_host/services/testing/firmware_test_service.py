# mara_host/services/testing/firmware_test_service.py
"""
Firmware test service.

Provides a service layer interface for running firmware unit tests,
wrapping the TestBackend from the tooling backends.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

from mara_host.core.result import ServiceResult
from mara_host.services.tooling.backends import get_registry, TestRequest
from mara_host.services.tooling.backends.models import TestEnvironment, TestOutcome


@dataclass
class FirmwareTestResult:
    """Result of firmware test run."""
    success: bool
    return_code: int
    environments: List[str] = field(default_factory=list)
    output: str = ""
    error: str = ""


class FirmwareTestService:
    """
    Service for running firmware unit tests.

    Provides a clean service interface for firmware testing, wrapping the
    underlying TestBackend from the tooling backends registry.

    Example:
        service = FirmwareTestService()

        # List available backends
        backends = service.list_backends()

        # Run native tests
        result = service.run_tests(environments=["native"])

        # Run with filter
        result = service.run_tests(filter_pattern="test_encoder*")
    """

    def __init__(self, backend_name: str = "platformio"):
        """
        Initialize firmware test service.

        Args:
            backend_name: Name of the test backend to use
        """
        self._backend_name = backend_name
        self._registry = get_registry()

    def list_backends(self) -> List[str]:
        """List available test backends."""
        return self._registry.list_test_backends()

    def run_tests(
        self,
        environments: Optional[List[str]] = None,
        filter_pattern: Optional[str] = None,
        verbose: bool = False,
        project_dir: Optional[Path] = None,
    ) -> ServiceResult:
        """
        Run firmware unit tests.

        Args:
            environments: List of environments to test ("native", "device").
                          Defaults to ["native"].
            filter_pattern: Optional glob pattern to filter tests
            verbose: Enable verbose output
            project_dir: Optional project directory override

        Returns:
            ServiceResult with FirmwareTestResult data on success
        """
        # Convert string environments to enum
        env_list: List[TestEnvironment] = []
        if environments is None:
            environments = ["native"]

        for env_str in environments:
            try:
                env_list.append(TestEnvironment(env_str))
            except ValueError:
                return ServiceResult.failure(f"Unknown environment: {env_str}")

        # Get backend
        try:
            backend = self._registry.get_test(self._backend_name)
        except KeyError:
            available = self._registry.list_test_backends()
            return ServiceResult.failure(
                f"Unknown test backend '{self._backend_name}'. "
                f"Available: {', '.join(available) or '(none registered)'}"
            )

        # Build request
        request = TestRequest(
            environments=env_list,
            filter_pattern=filter_pattern,
            verbose=verbose,
            project_dir=project_dir,
        )

        # Run tests
        try:
            outcome: TestOutcome = backend.run_tests(request)

            result = FirmwareTestResult(
                success=outcome.success,
                return_code=outcome.return_code,
                environments=outcome.environments_run,
                output=outcome.output,
                error=outcome.error,
            )

            if outcome.success:
                return ServiceResult.success(
                    message="All tests passed",
                    data={"result": result},
                )
            else:
                return ServiceResult.failure(
                    f"Tests failed with exit code {outcome.return_code}",
                    data={"result": result},
                )

        except Exception as e:
            return ServiceResult.failure(f"Test execution failed: {e}")

    def run_native(
        self,
        filter_pattern: Optional[str] = None,
        verbose: bool = False,
    ) -> ServiceResult:
        """Convenience method to run native tests only."""
        return self.run_tests(
            environments=["native"],
            filter_pattern=filter_pattern,
            verbose=verbose,
        )

    def run_device(
        self,
        filter_pattern: Optional[str] = None,
        verbose: bool = False,
    ) -> ServiceResult:
        """Convenience method to run device tests only."""
        return self.run_tests(
            environments=["device"],
            filter_pattern=filter_pattern,
            verbose=verbose,
        )
