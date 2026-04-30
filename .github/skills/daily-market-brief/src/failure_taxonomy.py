from __future__ import annotations

from enum import Enum


class FailureClass(str, Enum):
    """Canonical failure classes used in run-summary attempted_sources entries."""

    DEPENDENCY_MISSING = "dependency_missing"
    NETWORK_TIMEOUT = "network_timeout"
    HTTP_NON_2XX = "http_non_2xx"
    PARSE_EMPTY = "parse_empty"
    SOURCE_SCHEMA_CHANGED = "source_schema_changed"
    UNKNOWN = "unknown"

    @classmethod
    def from_exception(cls, exc: BaseException) -> "FailureClass":
        """Heuristically classify an exception into a FailureClass."""
        import socket

        name = type(exc).__name__.lower()
        msg = str(exc).lower()
        if isinstance(exc, ImportError):
            return cls.DEPENDENCY_MISSING
        if isinstance(exc, (TimeoutError, socket.timeout)) or "timeout" in msg:
            return cls.NETWORK_TIMEOUT
        if "http" in name or any(kw in msg for kw in ("status", "403", "404", "500", "non-2xx")):
            return cls.HTTP_NON_2XX
        if any(kw in msg for kw in ("parse", "empty", "schema", "unexpected field", "key error", "index error")):
            return cls.SOURCE_SCHEMA_CHANGED
        return cls.UNKNOWN
