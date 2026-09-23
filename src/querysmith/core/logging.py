"""Allowlist-only structured logging."""

import logging
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

_ALLOWED = {
    "event",
    "level",
    "timestamp",
    "request_id",
    "query_id",
    "user_id",
    "route",
    "status",
    "duration_ms",
    "error_code",
}


def sanitize_event(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    return {key: value for key, value in event_dict.items() if key in _ALLOWED}


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            sanitize_event,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
