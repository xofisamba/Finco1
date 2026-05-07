"""Structured logging setup for FincoGPT."""
import logging
import os
import time
from pathlib import Path

LOG_DIR = Path("/opt/finco1/logs")
LOG_FILE = LOG_DIR / "app.log"
LOGGER_NAME = "fincogpt"

# App-level metrics (process-global, updated by middleware and error handler)
_start_time = time.monotonic()
_total_requests = 0
_total_errors = 0


def setup_logging() -> None:
    """Configure the 'fincogpt' logger.

    Log format: timestamp | level | module | message
    Two handlers:
      - file handler  → /opt/finco1/logs/app.log (rotating, 10 MB, 5 backups)
      - console handler → stderr (info+)
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — rotating, 10 MB per file, keep 5 backups
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler — stderr at INFO+
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Logging initialised — file=%s", LOG_FILE)


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a logger descendant of 'fincogpt'."""
    return logging.getLogger(name)


def increment_requests() -> None:
    global _total_requests
    _total_requests += 1


def increment_errors() -> None:
    global _total_errors
    _total_errors += 1


def get_metrics() -> dict:
    """Return app-level metrics."""
    return {
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
        "total_requests": _total_requests,
        "total_errors": _total_errors,
    }
