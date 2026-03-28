# mara_host/logging/logger.py
"""
Logging infrastructure for MARA host.

Provides:
- Logger: Traditional rotating file logger with dedup
- JsonlLogger: JSONL flight recorder for structured events
- StructuredLogger: Context-aware logger with correlation IDs
- MaraLogBundle: Convenience wrapper combining text and JSONL logging
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, is_dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional, Dict

# Context variable for correlation ID propagation across async calls
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


class DedupFilter(logging.Filter):
    """
    Suppress repeated messages per (logger_name, level) within a cooldown window.
    This avoids global suppression that can hide important events from other subsystems.
    """
    def __init__(self, cooldown_s: float = 0.0) -> None:
        super().__init__()
        self.cooldown_s = float(cooldown_s)
        self._lock = threading.Lock()
        self._last: dict[tuple[str, int], tuple[str, float]] = {}  # (name, level) -> (msg, ts)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        now = time.time()
        key = (record.name, record.levelno)

        with self._lock:
            last = self._last.get(key)
            if last is not None:
                last_msg, last_ts = last
                if msg == last_msg:
                    if self.cooldown_s <= 0.0:
                        return False
                    if (now - last_ts) < self.cooldown_s:
                        return False

            self._last[key] = (msg, now)
            return True


class Logger:
    """
    Thread-safe rotating logger with per-(logger, level) dedup suppression.

    - Rotating file handler prevents huge logs during long soaks.
    - DedupFilter reduces spam without hiding unrelated subsystem messages.
    """
    def __init__(
        self,
        log_file: str,
        logger_name: str,
        log_dir: str = "logs",
        level: int = logging.INFO,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
        propagate: bool = False,
        max_bytes: int = 5_000_000,
        backup_count: int = 5,
        console: bool = False,
        dedup_cooldown_s: float = 0.0,
    ) -> None:
        os.makedirs(log_dir, exist_ok=True)
        full_log_path = os.path.join(log_dir, log_file)

        _logger = logging.getLogger(logger_name)
        _logger.setLevel(level)
        _logger.propagate = propagate

        # Avoid duplicate handlers if logger already exists (common in pytest)
        if not _logger.handlers:
            fmt = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt=timestamp_format,
            )

            fh = RotatingFileHandler(
                full_log_path,
                maxBytes=int(max_bytes),
                backupCount=int(backup_count),
            )
            fh.setLevel(level)
            fh.setFormatter(fmt)
            fh.addFilter(DedupFilter(cooldown_s=dedup_cooldown_s))
            _logger.addHandler(fh)

            if console:
                ch = logging.StreamHandler()
                ch.setLevel(level)
                ch.setFormatter(fmt)
                ch.addFilter(DedupFilter(cooldown_s=dedup_cooldown_s))
                _logger.addHandler(ch)

        self._logger = _logger
        self._logger.debug(f"Logger '{logger_name}' initialized → {full_log_path}")

    def get_logger(self) -> logging.Logger:
        return self._logger

    def debug(self, msg: str, *args, **kwargs) -> None: self._logger.debug(msg, *args, **kwargs)
    def info(self, msg: str, *args, **kwargs) -> None: self._logger.info(msg, *args, **kwargs)
    def warning(self, msg: str, *args, **kwargs) -> None: self._logger.warning(msg, *args, **kwargs)
    def error(self, msg: str, *args, **kwargs) -> None: self._logger.error(msg, *args, **kwargs)
    def critical(self, msg: str, *args, **kwargs) -> None: self._logger.critical(msg, *args, **kwargs)


class JsonlLogger:
    """
    Simple JSONL "flight recorder" for soaks + research mode.
    Each call appends one JSON object per line (buffered=1 for near-real-time).
    """
    def __init__(self, path: str, mkdirs: bool = True) -> None:
        self.path = str(path)
        if mkdirs:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._f = open(self.path, "a", buffering=1, encoding="utf-8")

    def write(self, event: str, **data: Any) -> None:
        row = {
            "ts_ns": time.time_ns(),
            "event": event,
            **self._normalize(data),
        }
        line = json.dumps(row, ensure_ascii=False, default=str)
        with self._lock:
            self._f.write(line + "\n")

    def close(self) -> None:
        with self._lock:
            try:
                self._f.close()
            except Exception:
                pass

    def __enter__(self) -> "JsonlLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _normalize(self, obj: Any) -> Any:
        """
        Make common objects JSON-friendly:
        - dataclasses -> dict
        - Path -> str
        - bytes -> base16-ish safe string
        - exceptions -> repr
        """
        if isinstance(obj, dict):
            return {k: self._normalize(v) for k, v in obj.items()}

        if isinstance(obj, (list, tuple)):
            return [self._normalize(v) for v in obj]

        if is_dataclass(obj):
            return self._normalize(asdict(obj))

        if isinstance(obj, Path):
            return str(obj)

        if isinstance(obj, bytes):
            # Avoid huge blobs; keep short summary + hex prefix
            if len(obj) <= 64:
                return {"bytes_len": len(obj), "hex": obj.hex()}
            return {"bytes_len": len(obj), "hex_prefix": obj[:64].hex()}

        if isinstance(obj, BaseException):
            return repr(obj)

        return obj


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID in context.

    Args:
        correlation_id: ID to set, or None to generate a new UUID

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]  # Short UUID for readability
    _correlation_id.set(correlation_id)
    return correlation_id


class StructuredLogger:
    """
    Structured logger with correlation IDs and subsystem tags.

    Provides context-aware logging that enables request tracing across
    async operations and subsystems.

    Features:
    - Automatic correlation ID propagation
    - Subsystem tagging for filtering
    - Structured metadata in each log entry
    - JSONL output for machine parsing

    Example:
        log = StructuredLogger("commander", jsonl_path="logs/events.jsonl")

        # Set correlation ID for a request
        with log.correlation_context("req-123"):
            log.info("command.sent", cmd_type="CMD_ARM", seq=42)
            # ... async work ...
            log.info("command.ack", seq=42, latency_ms=15.2)

        # Later, grep by correlation_id to trace the full request
    """

    def __init__(
        self,
        subsystem: str,
        jsonl_path: Optional[str] = None,
        writer: Optional[JsonlLogger] = None,
    ):
        """
        Initialize structured logger.

        Args:
            subsystem: Subsystem name (e.g., "commander", "telemetry")
            jsonl_path: Path to JSONL file (creates new writer)
            writer: Existing JsonlLogger to use (alternative to jsonl_path)
        """
        self._subsystem = subsystem

        if writer is not None:
            self._writer = writer
        elif jsonl_path is not None:
            self._writer = JsonlLogger(jsonl_path)
        else:
            self._writer = None

    def log(
        self,
        event: str,
        level: str = "info",
        correlation_id: Optional[str] = None,
        **context: Any,
    ) -> None:
        """
        Log a structured event.

        Args:
            event: Event name (e.g., "cmd.sent", "telem.gap")
            level: Log level (debug, info, warning, error)
            correlation_id: Override correlation ID (uses context var if None)
            **context: Additional context fields
        """
        if self._writer is None:
            return

        # Use provided correlation_id or get from context
        cid = correlation_id or get_correlation_id()

        entry: Dict[str, Any] = {
            "subsystem": self._subsystem,
            "level": level,
        }

        if cid:
            entry["correlation_id"] = cid

        # Merge context
        entry.update(context)

        self._writer.write(event, **entry)

    def debug(self, event: str, **context: Any) -> None:
        """Log debug-level event."""
        self.log(event, level="debug", **context)

    def info(self, event: str, **context: Any) -> None:
        """Log info-level event."""
        self.log(event, level="info", **context)

    def warning(self, event: str, **context: Any) -> None:
        """Log warning-level event."""
        self.log(event, level="warning", **context)

    def error(self, event: str, **context: Any) -> None:
        """Log error-level event."""
        self.log(event, level="error", **context)

    def correlation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for correlation ID scope.

        Args:
            correlation_id: ID to use, or None to generate

        Returns:
            Context manager that sets/restores correlation ID

        Example:
            with log.correlation_context("req-42"):
                log.info("start")
                await do_work()
                log.info("done")
        """
        return _CorrelationContext(correlation_id)

    def child(self, subsystem: str) -> "StructuredLogger":
        """
        Create a child logger with a different subsystem tag.

        Shares the same writer, so all logs go to the same file.

        Args:
            subsystem: New subsystem name

        Returns:
            New StructuredLogger with shared writer
        """
        return StructuredLogger(subsystem, writer=self._writer)

    def close(self) -> None:
        """Close the underlying writer if owned."""
        if self._writer is not None:
            self._writer.close()


class _CorrelationContext:
    """Context manager for correlation ID scope."""

    def __init__(self, correlation_id: Optional[str] = None):
        self._new_id = correlation_id
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> str:
        old_id = _correlation_id.get()
        new_id = self._new_id if self._new_id else str(uuid.uuid4())[:8]
        self._token = _correlation_id.set(new_id)
        return new_id

    def __exit__(self, *args) -> None:
        if self._token is not None:
            _correlation_id.reset(self._token)


class MaraLogBundle:
    """
    Convenience wrapper: a human-readable rotating Logger + a JSONL event logger.

    Provides both traditional text logging and structured JSONL logging.
    The structured logger shares the same JSONL writer for unified output.
    """

    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        level: int = logging.INFO,
        console: bool = False,
        max_bytes: int = 5_000_000,
        backup_count: int = 5,
        dedup_cooldown_s: float = 0.0,
        jsonl_file: Optional[str] = None,
        text_file: Optional[str] = None,
    ) -> None:
        text_file = text_file or f"{name}.log"
        jsonl_file = jsonl_file or f"{name}.jsonl"

        self.text = Logger(
            log_file=text_file,
            logger_name=name,
            log_dir=log_dir,
            level=level,
            console=console,
            max_bytes=max_bytes,
            backup_count=backup_count,
            dedup_cooldown_s=dedup_cooldown_s,
        )
        self.events = JsonlLogger(path=str(Path(log_dir) / jsonl_file))

        # Structured logger sharing the same JSONL writer
        self.structured = StructuredLogger(name, writer=self.events)

    def child_logger(self, subsystem: str) -> StructuredLogger:
        """
        Create a child structured logger for a specific subsystem.

        Args:
            subsystem: Subsystem name (e.g., "commander", "telemetry")

        Returns:
            StructuredLogger that writes to the same JSONL file
        """
        return StructuredLogger(subsystem, writer=self.events)

    def close(self) -> None:
        self.events.close()
