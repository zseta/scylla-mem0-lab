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


def why(event: CqlEvent, step: str, earlier: list[CqlEvent]) -> str:
    """A few words on why mem0 sent this statement, given the step it ran in ("mem0.search", ...)."""
    q = event.query.upper()
    entities = "_ENTITIES" in q  # memories_entities: names mem0 found in memories
    action = step.split()[0]
    deleting = action in ("mem0.delete", "mem0.delete_all")
    if q.startswith("SELECT") and "ANN OF" in q:
        if entities:
            return "Find memories mentioning this name" if action == "mem0.search" else "Is this name already stored?"
        if any("ANN OF" in e.query.upper() and "_ENTITIES" not in e.query.upper() for e in earlier):
            return "Filters dropped rows: fetch more"
        return "Existing memories, to skip duplicates" if action == "mem0.add" else "Find memories similar to the message"
    if q.startswith("SELECT"):
        if "WHERE ID = ?" in q:
            return "Read the memory first"
        if entities:
            return "Find names linked to this memory" if deleting else "Load known names (entities)"
        return "Find every memory to delete" if deleting else "List the customer's memories"
    if q.startswith("INSERT"):
        return "Store a new name (entity)" if entities else "Store the new memory"
    if q.startswith("UPDATE"):
        if not entities:
            return "Save new text and vector"
        if deleting:
            return "Unlink name from deleted memory"
        return "Update the name's memory links" if action == "mem0.update" else "Link name to this memory"
    if q.startswith("DELETE"):
        return "Drop name, no memories left" if entities else "Delete the memory"
    return ""


def format_event(event: CqlEvent) -> str:
    """One statement as readable CQL, with bound values as a comment."""
    text = event.query
    for keyword in (" FROM ", " WHERE ", " ORDER BY ", " LIMIT ", " VALUES ", " SET ", " USING ", " WITH "):
        text = text.replace(keyword, "\n " + keyword.strip() + " ")
    if event.params:
        text += "\n-- values: " + ", ".join(repr(p) if isinstance(p, str) else str(p) for p in event.params)
    return text
