# mara_host/logger/__init__.py
"""
Logging infrastructure for MARA.

Provides both traditional per-instance loggers and centralized logging.

Centralized logging (recommended):
    from mara_host.logger import init_mara_logging, get_logger

    # At app startup:
    init_mara_logging()

    # In any module:
    logger = get_logger("transport")
    logger.info("Connected")

    # Capture MCU logs:
    cleanup = attach_mcu_log_capture(client.bus)

Per-instance logging (legacy):
    from mara_host.logger import MaraLogBundle

    bundle = MaraLogBundle(name="session", log_dir="logs")
    bundle.text.info("message")
"""

from .logger import (
    Logger,
    JsonlLogger,
    MaraLogBundle,
    DedupFilter,
    StructuredLogger,
    get_correlation_id,
    set_correlation_id,
)

from .central import (
    init_mara_logging,
    get_logger,
    get_events_logger,
    log_event,
    attach_mcu_log_capture,
    set_mcu_log_level,
    shutdown_logging,
)

__all__ = [
    # Centralized logging (preferred)
    "init_mara_logging",
    "get_logger",
    "get_events_logger",
    "log_event",
    "attach_mcu_log_capture",
    "set_mcu_log_level",
    "shutdown_logging",
    # Per-instance logging (legacy)
    "Logger",
    "JsonlLogger",
    "MaraLogBundle",
    "DedupFilter",
    "StructuredLogger",
    # Correlation ID utilities
    "get_correlation_id",
    "set_correlation_id",
]
