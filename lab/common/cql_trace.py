"""Capture every CQL statement mem0 sends to ScyllaDB, with its latency.

Wraps the driver's Session.execute_async (Session.execute calls it too), so statements
are captured from the moment a session exists, including the DDL mem0 runs at startup.
"""

import threading
import time
from dataclasses import dataclass

from cassandra.cluster import Session

from common.config import KEYSPACE


@dataclass
class CqlEvent:
    query: str
    params: list
    started: float
    elapsed_ms: float | None = None
    error: str | None = None


_events: list[CqlEvent] = []
_lock = threading.Lock()
_installed = False


def _query_text(query) -> str:
    if isinstance(query, str):
        return query
    text = getattr(query, "query_string", None)
    if text is None and getattr(query, "prepared_statement", None) is not None:
        text = query.prepared_statement.query_string
    return text or str(query)


def _show(value):
    if isinstance(value, (list, tuple)) and len(value) > 8 and all(isinstance(v, float) for v in value):
        return f"<vector: {len(value)} floats>"
    if isinstance(value, str) and len(value) > 120:
        return value[:117] + "..."
    return value


def _query_params(query, parameters) -> list:
    values = parameters if parameters is not None else getattr(query, "raw_values", None)
    if values is None:
        return []
    if isinstance(values, dict):
        return [f"{k}={_show(v)}" for k, v in values.items()]
    return [_show(v) for v in values]


def install():
    """Patch the driver once per process."""
    global _installed
    if _installed:
        return
    _installed = True
    original = Session.execute_async

    def execute_async(self, query, parameters=None, *args, **kwargs):
        future = original(self, query, parameters, *args, **kwargs)
        text = " ".join(_query_text(query).split())
        if KEYSPACE in text or not text.lower().startswith("select"):
            event = CqlEvent(text, _query_params(query, parameters), time.perf_counter())
            with _lock:
                _events.append(event)
                del _events[:-2000]

            def done(_result, e=event):
                e.elapsed_ms = (time.perf_counter() - e.started) * 1000

            def failed(exc, e=event):
                done(None, e)
                e.error = str(exc)

            future.add_callbacks(done, failed)
        return future

    Session.execute_async = execute_async


def mark() -> int:
    with _lock:
        return len(_events)


def since(position: int) -> list[CqlEvent]:
    time.sleep(0.01)  # let driver callbacks record the last latencies
    with _lock:
        return list(_events[position:])


def format_event(event: CqlEvent) -> str:
    """One statement as readable CQL, with bound values as a comment."""
    text = event.query
    for keyword in (" FROM ", " WHERE ", " ORDER BY ", " LIMIT ", " VALUES ", " SET ", " USING ", " WITH "):
        text = text.replace(keyword, "\n " + keyword.strip() + " ")
    if event.params:
        text += "\n-- values: " + ", ".join(repr(p) if isinstance(p, str) else str(p) for p in event.params)
    return text
