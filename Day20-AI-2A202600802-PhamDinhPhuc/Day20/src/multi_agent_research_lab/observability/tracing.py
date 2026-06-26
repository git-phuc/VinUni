"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any


import logging

logger = logging.getLogger(__name__)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Trace execution span and log details, integrating with standard logs."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    logger.info(f"Span [ {name} ] started. Attributes: {attributes or {}}")
    try:
        yield span
    finally:
        duration = perf_counter() - started
        span["duration_seconds"] = duration
        logger.info(f"Span [ {name} ] completed in {duration:.4f}s")

