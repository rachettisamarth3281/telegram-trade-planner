import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

class StructuredJsonFormatter(logging.Formatter):
    """
    JSON Formatter for structured logging across all services.
    Outputs ISO-8601 UTC timestamps, log levels, logger name, and extra context.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include location info in debug mode or for errors
        if record.levelno >= logging.ERROR or record.exc_info:
            log_entry["module"] = record.module
            log_entry["funcName"] = record.funcName
            log_entry["line"] = record.lineno

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if provided
        for key, val in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName"
            } and not key.startswith("_"):
                log_entry[key] = val

        return json.dumps(log_entry, default=str)

class StructuredLogger:
    """Wrapper around standard Logger that converts arbitrary kwargs into extra dict."""
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

    def _log(self, level: int, msg: str, *args, **kwargs):
        exc_info = kwargs.pop("exc_info", None)
        stack_info = kwargs.pop("stack_info", False)
        extra = kwargs.pop("extra", {}) or {}
        if kwargs:
            extra.update(kwargs)
        self._logger._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info)

def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configures root logger with standard or JSON formatting."""
    root = logging.getLogger()
    root.setLevel(log_level.upper())

    # Clear existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    root.addHandler(handler)

def get_logger(name: str) -> StructuredLogger:
    """Helper to get a structured named logger."""
    return StructuredLogger(logging.getLogger(name))
