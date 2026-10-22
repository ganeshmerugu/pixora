from __future__ import annotations
import logging
import json
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "document_id"):
            log_entry["document_id"] = record.document_id  # type: ignore[attr-defined]
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id  # type: ignore[attr-defined]
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent  # type: ignore[attr-defined]
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data  # type: ignore[attr-defined]

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("pixora")
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def get_logger(name: str = "pixora") -> logging.Logger:
    return logging.getLogger(name)
