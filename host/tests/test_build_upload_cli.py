"""Tests for upload CLI command using backend abstraction."""

import argparse
from dataclasses import dataclass
from unittest.mock import MagicMock

from mara_host.cli.commands.build.upload import DEFAULT_DIRECT_UPLOAD_BAUD, cmd_upload
from mara_host.services.build.backends import BuildOutcome, FlashOutcome


def _args(**overrides):
    base = {
        "env": "esp32_usb",
        "verbose": False,
        "port": "/dev/ttyUSB0",
        "features": None,
        "preset": None,
        "no_features": None,
        "dry_run": False,
        "generate": False,
        "upload_baud": None,
        "direct": False,
        "auto_retry_direct": False,
        "build_backend": "platformio",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _make_mock_registry(build_success=True, flash_outcomes=None):
    """Create a mock registry with configurable outcomes.

    Args:
        build_success: Whether build should succeed
        flash_outcomes: List of FlashOutcome objects for sequential flash calls
    """
    if flash_outcomes is None:
        flash_outcomes = [FlashOutcome(success=True, return_code=0)]

    flash_call_count = [0]
    flash_calls = []
    build_calls = []

    mock_build = MagicMock()
    mock_build.build = MagicMock(side_effect=lambda req: (
        build_calls.append(req),
        BuildOutcome(success=build_success, return_code=0 if build_success else 1)
    )[1])

    mock_flash = MagicMock()
    def flash_side_effect(req):
        flash_calls.append(req)
        idx = flash_call_count[0]
        flash_call_count[0] += 1
        if idx < len(flash_outcomes):
            return flash_outcomes[idx]
        return flash_outcomes[-1]
    mock_flash.flash = MagicMock(side_effect=flash_side_effect)

    mock_registry = MagicMock()
    mock_registry.get_build = MagicMock(return_value=mock_build)
    mock_registry.get_flash = MagicMock(return_value=mock_flash)

    return mock_registry, build_calls, flash_calls


def test_cmd_upload_passes_direct_options(monkeypatch):
    """Test that direct flash options are passed to the backend."""
    mock_registry, build_calls, flash_calls = _make_mock_registry()
    monkeypatch.setattr(
        "mara_host.cli.commands.build.upload.get_registry",
        lambda: mock_registry
    )

    rc = cmd_upload(_args(upload_baud=57600, direct=True))

    assert rc == 0
    # With direct=True, build is called first
    assert len(build_calls) == 1
    assert build_calls[0].environment == "esp32_usb"
    # Then flash
    assert len(flash_calls) == 1
    assert flash_calls[0].port == "/dev/ttyUSB0"
    assert flash_calls[0].baud == 57600
    assert flash_calls[0].direct is True


def test_cmd_upload_auto_retries_direct_on_failure(monkeypatch):
    """Test that upload auto-retries with direct mode on failure."""
    # First flash fails, second succeeds
    flash_outcomes = [
        FlashOutcome(success=False, return_code=7),
        FlashOutcome(success=True, return_code=0),
    ]
    mock_registry, build_calls, flash_calls = _make_mock_registry(
        flash_outcomes=flash_outcomes
    )
    monkeypatch.setattr(
        "mara_host.cli.commands.build.upload.get_registry",
        lambda: mock_registry
    )

    rc = cmd_upload(_args(auto_retry_direct=True))

    assert rc == 0
    # First attempt via PIO (no build call since PIO does build+upload)
    # Second attempt is direct, so it builds first
    assert len(build_calls) == 1
    # Two flash attempts
    assert len(flash_calls) == 2
    # First attempt: not direct
    assert flash_calls[0].direct is False
    # Second attempt: direct mode
    assert flash_calls[1].direct is True
    assert flash_calls[1].baud == DEFAULT_DIRECT_UPLOAD_BAUD


def test_cmd_upload_does_not_retry_direct_without_port(monkeypatch):
    """Test that auto-retry requires a port."""
    flash_outcomes = [FlashOutcome(success=False, return_code=9)]
    mock_registry, build_calls, flash_calls = _make_mock_registry(
        flash_outcomes=flash_outcomes
    )
    monkeypatch.setattr(
        "mara_host.cli.commands.build.upload.get_registry",
        lambda: mock_registry
    )

    rc = cmd_upload(_args(port=None, auto_retry_direct=True))

    assert rc == 9
    # Only one flash attempt since no port for retry
    assert len(flash_calls) == 1
    assert flash_calls[0].port is None
