from __future__ import annotations

import logging
import sys

import structlog

from core.config import settings

def configure_logging(json_output: bool = False, level: str | None = None) -> None:
    json_output = json_output or settings.log_json
    level = level or settings.log_level
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, level.upper()))

    renderer = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(colors=False)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    return structlog.get_logger(name)
