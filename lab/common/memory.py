"""Builds a mem0 Memory connected to ScyllaDB, with CQL capture switched on."""

import logging

from common import cql_trace, gemini
from common.config import mem0_config

# The ScyllaDB provider has no keyword (BM25) search yet; mem0 warns about it on every start.
logging.getLogger("mem0.memory.main").setLevel(logging.ERROR)


def create_memory(**overrides):
    cql_trace.install()
    gemini.install()
    from mem0 import Memory

    memory = Memory.from_config(mem0_config(**overrides))
    _ = memory.entity_store  # created lazily; create it now so its DDL is not part of the first chat turn
    memory.embedding_model.embed("warm up", "search")  # first call loads the model; keep it out of the first turn
    return memory


def set_consistency(memory, level):
    """Apply a consistency level to every ScyllaDB session mem0 uses."""
    for store in (memory.vector_store, memory.entity_store):
        store.session.default_consistency_level = level
