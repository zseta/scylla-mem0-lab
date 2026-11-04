# 05 · Memory lifecycle: update, delete, history

mem0 v3 only adds memories. When a fact changes ("I moved to Lisbon"), the old fact ("lives in Berlin") stays and both come back in search. Keeping memories correct is the application's job:

| Call | Use |
|---|---|
| `get_all(filters={"user_id": ...})` | list a customer's memories |
| `update(memory_id, text=...)` | correct one memory |
| `delete(memory_id)` | remove one memory |
| `history(memory_id)` | see how a memory changed |
| `delete_all(user_id=...)` | forget a customer completely |

This exercise adds a **Rep dashboard** tab for a human support rep. From here on, `add()` also records the bot (`agent_id`) and the ticket (`run_id`). `search()` still looks only at the customer's memories (`user_id`).

## Exercise

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/05-memory-lifecycle && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. Nora moves to Lisbon, then asks where her next order ships. Open the `mem0.search` step: Berlin and Lisbon both come back.
3. **App**: open **Rep dashboard** (customer `nora`):
   - **Delete** what is wrong: every memory that puts her address in Berlin. Keep the order #4821 memories.
   - **Delete** duplicates, such as a second "User's name is Nora".
   - **Edit** one memory, then click **History** on it.
4. **App**: back in **Chat**, open a **New ticket** and ask *Which address will you ship my next order to?*
5. Optional: select `erik`, tick the checkbox, and click **Forget erik · delete_all()**.

## Under the hood

The dashboard's panel shows the CQL of each action:

```sql
-- delete(): read the memory, delete it, unlink its entities
SELECT id, payload FROM plushie_shop.memories WHERE id = ?;
DELETE FROM plushie_shop.memories WHERE id = ?;
SELECT id, payload FROM plushie_shop.memories_entities WHERE user_id = ?;
DELETE FROM plushie_shop.memories_entities WHERE id = ?;

-- update(): new text, new vector, same id
UPDATE plushie_shop.memories SET vector = ?, ... payload = ? WHERE id = ?;
```

- A delete in ScyllaDB writes a **tombstone**, a marker that hides the row until compaction removes it. Deletes are as fast as writes.
- The vector index picks up updates and deletes through CDC, usually within a second.
- `add()` looks for duplicates only inside the scope it writes to. With `run_id` set, every new ticket starts from zero, so facts like "User's name is Nora" are stored again.
- `history()` shows **no CQL**: mem0 keeps history in a local SQLite file, not in ScyllaDB.

**Takeaway:** memory needs maintenance. Give people tools to fix and forget.
