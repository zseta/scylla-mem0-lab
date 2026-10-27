# 09 · Performance and scale

> This lab VM is small, with 3 nodes on one machine and 1 CPU core each. The numbers show where time goes, not what production hardware does.

A memory turn has three costs:

| Step | Where the time goes | Customer waits? |
|---|---|---|
| `search()` | embed the question (CPU) + one ANN query | yes |
| LLM reply | Gemini | yes |
| `add()` | Gemini extraction + embed + writes | **no need** |

## Do

1. **Terminal**: start this exercise's bot. `add()` now runs in a background thread.

   ```bash
   cd ~/mem0-lab/lab/exercise/09-performance && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. `mem0.add` takes about 0 ms: the reply no longer waits for it.
   The trade-off: a memory is searchable only after the background `add()` finishes and the index catches up, a few seconds later. The scenario waits 6 seconds before the second question.
3. **Terminal**: load 1,000 memories for 200 customers, then benchmark search with 8 threads. This makes **no** Gemini calls (`add(infer=False)`).

   ```bash
   ./load.sh 200 8 10
   ```

4. Compare the two lines of the result. On a laptop we measured:

   ```text
   test                        req/s   p50 ms   p95 ms   p99 ms
   mem0.search()                  16    346.5   2429.5   2688.3
   ScyllaDB ANN query            426     17.3     30.3     37.1
   ```

## What the numbers say

- The database is not the bottleneck. The ANN query is fast and steady.
- `mem0.search()` is slower because Python embeds each question on CPU and extracts entities with spaCy, and the threads compete for the CPU.

## Techniques for real scale

- **Keep `add()` off the hot path**: background workers or a queue.
- **Scale the app tier**: more processes or pods. Embedding is CPU work.
- **Faster embeddings**: GPU, a hosted embedding API, or batching.
- **Small `top_k`** (5–10): fewer rows, smaller prompts.
- **Choose embedding dimensions on purpose**: the size is fixed in the `VECTOR<FLOAT, N>` column.
- **Driver settings**: prepared statements (the provider uses them), `datacenter` set to the local DC, and token-aware routing (`TokenAwarePolicy`), so each request goes straight to a replica and the core that owns the row.
- **Bigger ScyllaDB nodes**: more cores means more shards. ScyllaDB Cloud scales nodes and the Vector Store for you.

**Takeaway:** measure each layer. Make the database the last thing you have to scale.
