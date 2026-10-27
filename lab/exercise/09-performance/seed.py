"""Load many customers' memories, without any LLM call.

add(infer=False) stores the text as-is: no fact extraction, no Gemini quota used.
Embedding runs on CPU; the writes go to ScyllaDB from several threads at once.

Usage: python seed.py [customers] [memories_per_customer] [threads]
"""

import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from common.memory import create_memory

CUSTOMERS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
PER_CUSTOMER = int(sys.argv[2]) if len(sys.argv) > 2 else 5
THREADS = int(sys.argv[3]) if len(sys.argv) > 3 else 8

CITIES = ["Berlin", "Lisbon", "Oslo", "Austin", "Kyoto", "Lyon", "Toronto", "Krakow", "Dublin", "Porto"]
FACTS = [
    "Prefers {contact} for order updates",
    "Ordered a {size} Scylla plushie, order #{order}",
    "Ships to {city}",
    "Asked about gift wrapping for a birthday",
    "Had a late delivery on order #{order}",
    "Was charged twice for order #{order}, refund requested",
    "Wants a wool-free plushie",
    "Collects ScyllaDB plushies, owns {n}",
]


def fact(rng):
    return rng.choice(FACTS).format(
        contact=rng.choice(["email", "SMS", "phone"]), size=rng.choice(["small", "large"]),
        order=rng.randint(1000, 9999), city=rng.choice(CITIES), n=rng.randint(2, 9),
    )


def seed_customer(i):
    rng = random.Random(i)
    user_id = f"load-{i:05d}"
    for _ in range(PER_CUSTOMER):
        memory.add(fact(rng), user_id=user_id, infer=False)


memory = create_memory()
total = CUSTOMERS * PER_CUSTOMER
print(f"Seeding {total} memories: {CUSTOMERS} customers x {PER_CUSTOMER}, {THREADS} threads...")
started = time.perf_counter()
with ThreadPoolExecutor(THREADS) as pool:
    for done, _ in enumerate(pool.map(seed_customer, range(CUSTOMERS)), 1):
        if done % 50 == 0 or done == CUSTOMERS:
            elapsed = time.perf_counter() - started
            print(f"  {done * PER_CUSTOMER:>6} memories · {done * PER_CUSTOMER / elapsed:,.0f} memories/s")
print(f"Done in {time.perf_counter() - started:.1f}s")
