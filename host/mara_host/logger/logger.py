# mara_host/logging/logger.py
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, is_dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional


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


class MaraLogBundle:
    """
    Convenience wrapper: a human-readable rotating Logger + a JSONL event logger.
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

    def close(self) -> None:
        self.events.close()
