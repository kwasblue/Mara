# mara_host/logger/central.py
"""
Centralized logging system for MARA.

Provides Amsterdam-style centralized logging with:
- Single bootstrap initialization
- Factory function for per-component loggers
- MCU log capture from event bus
- Environment-driven configuration
- Unified combined log + JSONL events

Usage:
    from mara_host.logger import init_mara_logging, get_logger

    # At app startup (once):
    init_mara_logging(log_dir="logs")

    # In any module:
    logger = get_logger("transport")
    logger.info("Connected to device")

    # To capture MCU logs, call after client is connected:
    attach_mcu_log_capture(client.bus)
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

from .logger import DedupFilter, JsonlLogger, get_correlation_id

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("MARA_LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("MARA_LOG_DIR", "logs")
STRUCTURED_LOGS = os.getenv("MARA_STRUCTURED_LOGS", "false").lower() == "true"
CONSOLE_OUTPUT = os.getenv("MARA_CONSOLE_LOGS", "true").lower() == "true"

# MCU log filtering
# MARA_MCU_LOG_LEVEL: Default level for MCU logs (debug, info, warn, error, off)
# MARA_MCU_DEBUG_TAGS: Comma-separated tags to capture at DEBUG level (e.g., "servo,stepper")
MCU_LOG_LEVEL = os.getenv("MARA_MCU_LOG_LEVEL", "info").lower()
MCU_DEBUG_TAGS = set(
    tag.strip().lower()
    for tag in os.getenv("MARA_MCU_DEBUG_TAGS", "").split(",")
    if tag.strip()
)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_initialized = False
_root_logger: Optional[logging.Logger] = None
_jsonl_logger: Optional[JsonlLogger] = None
_mcu_handler: Optional[Callable] = None
_lock = threading.Lock()

# Track created loggers to avoid duplicates
_loggers: Dict[str, logging.Logger] = {}


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured log output.

    Outputs each log record as a single JSON line with:
    - timestamp, level, logger name, message
    - correlation_id (if set)
    - source location (file, line, function)
    - exception info (if present)
    - extra fields
    """

    # Fields that are part of the standard LogRecord, not extra
    STANDARD_FIELDS: Set[str] = {
        "name", "msg", "args", "created", "filename", "funcName", "levelname",
        "levelno", "lineno", "module", "msecs", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "exc_info", "exc_text",
        "thread", "threadName", "message", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Build structured log entry
        entry: Dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            entry["correlation_id"] = correlation_id

        # Add source location
        entry["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "func": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields (anything not in STANDARD_FIELDS)
        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in self.STANDARD_FIELDS and not k.startswith("_")
        }
        if extra:
            entry["extra"] = extra

        return json.dumps(entry, default=str, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "MCU": "\033[34m",       # Blue (for MCU logs)
    }
    RESET = "\033[0m"

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Check if this is an MCU log
        color_key = "MCU" if record.name.startswith("mcu.") else record.levelname
        color = self.COLORS.get(color_key, "")

        # Format the message
        formatted = super().format(record)

        if color and sys.stderr.isatty():
            return f"{color}{formatted}{self.RESET}"
        return formatted


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def init_mara_logging(
    log_dir: Optional[str] = None,
    level: Optional[str] = None,
    console: Optional[bool] = None,
    structured: Optional[bool] = None,
    session_name: Optional[str] = None,
) -> None:
    """
    Initialize centralized MARA logging.

    Call once at application startup. All subsequent get_logger() calls
    will use this configuration.

    Args:
        log_dir: Directory for log files (default: MARA_LOG_DIR env or "logs")
        level: Log level (default: MARA_LOG_LEVEL env or "INFO")
        console: Enable console output (default: MARA_CONSOLE_LOGS env or True)
        structured: Use JSON format (default: MARA_STRUCTURED_LOGS env or False)
        session_name: Session name for log files (default: timestamp)

    Example:
        init_mara_logging(log_dir="logs", level="DEBUG", console=True)
    """
    global _initialized, _root_logger, _jsonl_logger

    with _lock:
        if _initialized:
            return

        # Apply defaults from environment
        log_dir = log_dir or LOG_DIR
        level = level or LOG_LEVEL
        console = console if console is not None else CONSOLE_OUTPUT
        structured = structured if structured is not None else STRUCTURED_LOGS

        # Create log directory
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Generate session name if not provided
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Configure root logger
        _root_logger = logging.getLogger("mara")
        _root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        _root_logger.propagate = False  # Don't propagate to root

        # Clear any existing handlers
        _root_logger.handlers.clear()

        # File handler (always text format for human reading)
        log_file = Path(log_dir) / f"mara_{session_name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        file_handler.addFilter(DedupFilter(cooldown_s=1.0))
        _root_logger.addHandler(file_handler)

        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

            if structured:
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(ColoredFormatter(
                    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
                    datefmt="%H:%M:%S",
                ))
            console_handler.addFilter(DedupFilter(cooldown_s=0.5))
            _root_logger.addHandler(console_handler)

        # JSONL event logger for structured events
        jsonl_file = Path(log_dir) / f"mara_{session_name}.jsonl"
        _jsonl_logger = JsonlLogger(str(jsonl_file))

        _initialized = True

        # Log initialization
        _root_logger.info(
            f"MARA logging initialized: level={level}, dir={log_dir}, "
            f"console={console}, structured={structured}"
        )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific component.

    All loggers are children of the root "mara" logger, so they inherit
    its handlers and configuration.

    Args:
        name: Component name (e.g., "transport", "commander", "telemetry")

    Returns:
        Logger instance for the component

    Example:
        logger = get_logger("transport")
        logger.info("Connected to %s", device_path)
    """
    # Auto-initialize with defaults if not done
    if not _initialized:
        init_mara_logging()

    full_name = f"mara.{name}" if not name.startswith("mara.") else name

    with _lock:
        if full_name not in _loggers:
            logger = logging.getLogger(full_name)
            _loggers[full_name] = logger
        return _loggers[full_name]


def get_events_logger() -> Optional[JsonlLogger]:
    """
    Get the JSONL events logger for structured event recording.

    Returns:
        JsonlLogger instance or None if not initialized
    """
    if not _initialized:
        init_mara_logging()
    return _jsonl_logger


def log_event(event: str, **data: Any) -> None:
    """
    Log a structured event to the JSONL file.

    Args:
        event: Event name (e.g., "cmd.sent", "telem.received")
        **data: Event data fields

    Example:
        log_event("cmd.sent", cmd="CMD_ARM", seq=42, latency_ms=15.2)
    """
    if _jsonl_logger is not None:
        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            data["correlation_id"] = correlation_id
        _jsonl_logger.write(event, **data)


# ---------------------------------------------------------------------------
# MCU Log Capture
# ---------------------------------------------------------------------------

def attach_mcu_log_capture(
    bus: Any,
    min_level: Optional[str] = None,
    debug_tags: Optional[Set[str]] = None,
) -> Callable[[], None]:
    """
    Attach MCU log capture to an event bus.

    Subscribes to the "json" topic and captures MCU log messages,
    routing them through the centralized logging system.

    Filtering:
        - min_level: Default minimum level for all MCU logs
        - debug_tags: Tags that should be captured at DEBUG level regardless of min_level

    Args:
        bus: EventBus instance to subscribe to
        min_level: Override MARA_MCU_LOG_LEVEL (debug, info, warn, error, off)
        debug_tags: Override MARA_MCU_DEBUG_TAGS (set of tag names)

    Returns:
        Cleanup function to call when disconnecting

    Example:
        # Capture all logs at INFO+, but DEBUG for servo and stepper
        cleanup = attach_mcu_log_capture(
            client.bus,
            min_level="info",
            debug_tags={"servo", "stepper"}
        )
    """
    global _mcu_handler

    if not _initialized:
        init_mara_logging()

    mcu_logger = get_logger("mcu")

    # MCU log level mapping
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "off": logging.CRITICAL + 10,  # Higher than any level = disabled
    }

    # Use provided values or fall back to environment
    effective_min_level = min_level.lower() if min_level else MCU_LOG_LEVEL
    effective_debug_tags = debug_tags if debug_tags is not None else MCU_DEBUG_TAGS

    base_level = level_map.get(effective_min_level, logging.INFO)

    def handle_mcu_json(data: Dict[str, Any]) -> None:
        """Handle incoming JSON from MCU, extract logs."""
        if not isinstance(data, dict):
            return

        # Check if this is a LOG message
        if data.get("src") != "mcu" or data.get("type") != "LOG":
            return

        log_data = data.get("log", {})
        if not isinstance(log_data, dict):
            return

        # Extract log fields
        level_str = log_data.get("level", "info").lower()
        tag = log_data.get("tag", "unknown")
        tag_lower = tag.lower()
        msg = log_data.get("msg", "")
        ts_ms = log_data.get("ts_ms", 0)

        # Map level
        msg_level = level_map.get(level_str, logging.INFO)

        # Determine minimum level for this tag
        # If tag is in debug_tags, allow DEBUG level through
        if tag_lower in effective_debug_tags:
            tag_min_level = logging.DEBUG
        else:
            tag_min_level = base_level

        # Filter by minimum level
        if msg_level < tag_min_level:
            return

        # Create tagged logger for this MCU subsystem
        tagged_logger = get_logger(f"mcu.{tag_lower}")

        # Log with MCU timestamp in message
        tagged_logger.log(msg_level, "[%dms] %s", ts_ms, msg)

        # Also log to JSONL events
        log_event(
            "mcu.log",
            level=level_str,
            tag=tag,
            msg=msg,
            mcu_ts_ms=ts_ms,
        )

    # Subscribe to json topic
    bus.subscribe("json", handle_mcu_json)
    _mcu_handler = handle_mcu_json

    debug_tags_str = ",".join(effective_debug_tags) if effective_debug_tags else "none"
    mcu_logger.info(
        "MCU log capture attached (level=%s, debug_tags=%s)",
        effective_min_level, debug_tags_str
    )

    def cleanup() -> None:
        """Unsubscribe from event bus."""
        global _mcu_handler
        try:
            bus.unsubscribe("json", handle_mcu_json)
            mcu_logger.info("MCU log capture detached")
        except Exception:
            pass
        _mcu_handler = None

    return cleanup


def set_mcu_log_level(client: Any, level: str = "info") -> None:
    """
    Set the MCU's log level (what it sends to host).

    Args:
        client: MaraClient instance
        level: Log level ("debug", "info", "warn", "error", "off")

    Example:
        # Get verbose MCU logs
        await set_mcu_log_level(client, "debug")

        # Reduce MCU log traffic
        await set_mcu_log_level(client, "warn")
    """
    import asyncio

    async def _set():
        await client.send("CMD_SET_LOG_LEVEL", {"level": level})

    # Handle both sync and async contexts
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(_set())
    except RuntimeError:
        asyncio.run(_set())


def shutdown_logging() -> None:
    """
    Shutdown the logging system gracefully.

    Closes file handlers and the JSONL logger.
    Call at application exit.
    """
    global _initialized, _root_logger, _jsonl_logger, _loggers

    with _lock:
        if not _initialized:
            return

        # Close JSONL logger
        if _jsonl_logger is not None:
            _jsonl_logger.close()
            _jsonl_logger = None

        # Close root logger handlers
        if _root_logger is not None:
            for handler in _root_logger.handlers[:]:
                handler.close()
                _root_logger.removeHandler(handler)

        _loggers.clear()
        _initialized = False
