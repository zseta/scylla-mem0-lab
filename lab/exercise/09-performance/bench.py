"""Measure memory search latency under concurrent load. No LLM calls.

Two numbers per run:
  mem0.search()          = embed the question on CPU + ANN query in ScyllaDB
  ScyllaDB ANN query     = the database part alone (question embedded in advance)

Usage: python bench.py [threads] [seconds]
"""

import random
import statistics
import sys
import threading
import time

from common.memory import create_memory

THREADS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 10

QUESTIONS = [
    "Where should we ship the order?", "How does the customer want to be contacted?",
    "Did the customer have a billing problem?", "What did the customer order?",
    "Is there a late delivery?", "Any allergies or material preferences?",
]


def run(label, call):
    latencies, lock, stop = [], threading.Lock(), time.perf_counter() + SECONDS

    def worker(seed):
        rng = random.Random(seed)
        local = []
        while time.perf_counter() < stop:
            user_id = f"load-{rng.randrange(customers):05d}"
            started = time.perf_counter()
            call(rng, user_id)
            local.append((time.perf_counter() - started) * 1000)
        with lock:
            latencies.extend(local)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    q = statistics.quantiles(latencies, n=100)
    print(f"{label:<24} {len(latencies) / SECONDS:>8,.0f} {q[49]:>8.1f} {q[94]:>8.1f} {q[98]:>8.1f}")


memory = create_memory()
store = memory.vector_store
rows = store.session.execute(f"SELECT user_id FROM {store.keyspace}.{store.collection_name}")
customers = len({r.user_id for r in rows if (r.user_id or "").startswith("load-")})
if not customers:
    sys.exit("No seeded customers found. Run seed.py first.")
vectors = {q: memory.embedding_model.embed(q, "search") for q in QUESTIONS}

print(f"{THREADS} threads, {SECONDS:.0f}s per test, ~{customers} seeded customers\n")
print(f"{'test':<24} {'req/s':>8} {'p50 ms':>8} {'p95 ms':>8} {'p99 ms':>8}")
run("mem0.search()", lambda rng, uid: memory.search(rng.choice(QUESTIONS), filters={"user_id": uid}, top_k=5))
run("ScyllaDB ANN query", lambda rng, uid: store.search(
    query="", vectors=vectors[rng.choice(QUESTIONS)], top_k=5, filters={"user_id": uid}))
