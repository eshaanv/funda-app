"""
Logging configuration for the Funda App application.
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON for Cloud Run.

    Args:
        record (logging.LogRecord): Log record to serialize.

    Returns:
        str: JSON-serialized log entry.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = dict(record.__dict__)
        payload["time"] = datetime.now(UTC).isoformat()
        payload["severity"] = record.levelname
        payload["logger"] = record.name
        payload["message"] = record.getMessage()

        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """
    Configures structured logging for the application.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.addHandler(handler)
