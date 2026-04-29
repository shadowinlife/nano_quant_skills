from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        message = record.getMessage()
        run_id = getattr(record, "run_id", "-")
        return f"{timestamp} level={record.levelname} logger={record.name} run_id={run_id} message={message}"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger