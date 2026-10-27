"""Records what happens during one chat turn: timed steps and the CQL each step sent."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from common import cql_trace


@dataclass
class Step:
    name: str
    elapsed_ms: float = 0.0
    cql: list = field(default_factory=list)
    detail: object = None


@dataclass
class Turn:
    steps: list[Step] = field(default_factory=list)

    @contextmanager
    def step(self, name: str):
        """with turn.step("mem0.search") as s: ...   (set s.detail to show a result in the UI)"""
        s = Step(name)
        position = cql_trace.mark()
        started = time.perf_counter()
        try:
            yield s
        finally:
            s.elapsed_ms = (time.perf_counter() - started) * 1000
            s.cql = cql_trace.since(position)
            self.steps.append(s)
