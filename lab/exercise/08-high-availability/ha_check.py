"""Write a memory and read it back every second at QUORUM, and print the result.

Keep it running while you stop and start a node. No LLM calls (infer=False).
Stop with Ctrl+C.
"""

import time

from cassandra import ConsistencyLevel

from common.memory import create_memory, set_consistency

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"

memory = create_memory()
set_consistency(memory, ConsistencyLevel.QUORUM)
cluster = memory.vector_store.cluster

print("Every second: write a memory, then read it back by id, both at QUORUM. Ctrl+C to stop.\n")
n = 0
while True:
    n += 1
    up = sum(h.is_up for h in cluster.metadata.all_hosts())
    started = time.perf_counter()
    try:
        written = memory.add(f"Heartbeat number {n}", user_id="ha-check", infer=False)["results"][0]
        read = memory.get(written["id"])
        ms = (time.perf_counter() - started) * 1000
        print(f"{GREEN}OK{RESET}   #{n:<4} write + read {ms:6.0f} ms   nodes up: {up}/3  {DIM}{read['memory']}{RESET}")
    except Exception as e:
        print(f"{RED}FAIL{RESET} #{n:<4} nodes up: {up}/3  {type(e).__name__}: {str(e)[:120]}")
    time.sleep(1)
