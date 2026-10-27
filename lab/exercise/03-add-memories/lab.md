# 03 · Write memories with `add()`

The bot now calls `memory.add()` after every turn. mem0 reads the exchange and keeps only the facts worth remembering.

```python
memory.add(
    [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
    user_id=ctx["customer"],
)
```

What `add()` does:

1. **Extract**: one Gemini call turns the conversation into short facts, for example "User prefers email communication".
2. **Deduplicate**: it skips facts that are already stored.
3. **Embed**: bge-small turns each fact into a 384-dimension vector, on CPU.
4. **Store**: it writes each fact to ScyllaDB, and links the entities (people, places, products) in `memories_entities`.

mem0 v3 only **adds**. It never silently overwrites an old fact.

## Do

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/03-add-memories && ./run.sh
   ```

2. **App**: reload the tab, then click **▶ Play scenario**. Alice sends her first message.
3. **App**: in **Under the hood**, read the `mem0.add` step: the facts mem0 extracted, then the CQL. The `SELECT ... ANN OF` on `memories` is the deduplication lookup, then one `INSERT` per new fact. The statements on `memories_entities` link the entities.
4. **App**: click **Next ▶** twice. In the new ticket, the bot still forgets: it writes memories but does not read them yet. That last message has no new facts, so `mem0.add` runs only the lookup.
5. **Terminal**: look at Alice's memories in ScyllaDB.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT id, payload FROM memories WHERE user_id = 'alice';"
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories_entities WHERE user_id = 'alice';"
   ```

## Under the hood

```sql
INSERT INTO plushie_shop.memories (id, vector, user_id, agent_id, run_id, payload)
VALUES (?, ?, ?, ?, ?, ?);
```

- Every write goes to all 3 replicas. The commitlog makes it durable before ScyllaDB acknowledges it.
- About 1 second of `add()` is the Gemini call. The database part takes a few milliseconds.

**Takeaway:** memories are short facts plus vectors, stored per customer.
