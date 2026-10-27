"""Exercise 02: connect mem0 to ScyllaDB and print the schema statements it runs."""

import time

from common import cql_trace
from common.config import mem0_config
from common.memory import create_memory

BLUE, DIM, BOLD, RESET = "\033[38;5;39m", "\033[2m", "\033[1m", "\033[0m"

config = mem0_config()
print(f"{BOLD}mem0 config{RESET}")
print(f"  llm:          {config['llm']['provider']} / {config['llm']['config']['model']}")
print(f"  embedder:     {config['embedder']['provider']} / {config['embedder']['config']['model']}"
      f" ({config['embedder']['config']['embedding_dims']} dims, runs on CPU)")
vs = config["vector_store"]["config"]
print(f"  vector_store: scylladb / {vs['contact_points'][0]}, keyspace {vs['keyspace']}")
print()

print("Connecting (first run loads the embedding model)...")
started = time.perf_counter()
memory = create_memory()
print(f"Ready in {time.perf_counter() - started:.1f}s\n")

print(f"{BOLD}CQL statements mem0 ran on ScyllaDB:{RESET}\n")
for event in cql_trace.since(0):
    if event.query.lower().startswith("select"):
        continue  # skip the index readiness probes
    print(f"{BLUE}{cql_trace.format_event(event)};{RESET}")
    ms = f"{event.elapsed_ms:.0f} ms" if event.elapsed_ms is not None else ""
    print(f"{DIM}-- {ms}{'  (' + event.error + ')' if event.error else ''}{RESET}\n")
