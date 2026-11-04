# 06 · Metadata and filters

Tag memories with your own fields when you add them, then filter on those fields when you search:

```python
memory.add(messages, user_id=customer, agent_id=bot, run_id=ticket,
           metadata={"category": "billing", "order_id": "4821"})

memory.search(text, filters={"user_id": customer, "category": "billing"})
```

The bot sets `category` from the ticket category in the sidebar, and `order_id` when the message mentions `#1234`.

## Exercise

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/06-metadata && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**:
   - a **billing** ticket: Nora was charged twice,
   - a **product** ticket: is the plushie washable,
   - a **billing** ticket with **Search only this category** on: only billing memories come back.
3. **App**: turn the filter off and on, and ask the same question. Compare the `mem0.search` results.
4. **Terminal**: see where the metadata lives.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'nora';" | grep category
   ```

## Under the hood

One `search()` call, two places that filter:

```python
memory.search(text, filters={"user_id": "nora",      # → ScyllaDB: WHERE clause
                             "category": "billing"})  # → mem0: Python, after the query
```

What mem0's ScyllaDB provider does, simplified:

```python
rows = session.execute(
    "SELECT id, score, payload FROM memories "
    "WHERE user_id = 'nora' ORDER BY vector ANN OF ? LIMIT 10")    # no category in the CQL
results = [r for r in rows
           if json.loads(r.payload).get("category") == "billing"]  # filtered in mem0
# fewer than 10 left? same query again with LIMIT 40, 160, ...
```

- Metadata is stored inside the `payload` JSON column, not in its own column. ScyllaDB can't filter on it.
- `user_id`, `agent_id` and `run_id` are real columns, so those filters run **in ScyllaDB**, inside the vector query.
- The CQL trace is the same with the filter on or off. Only the `mem0.search` results change.

**Design lesson:** a field you filter on all the time belongs in a real column, so the database can filter on it.

**Takeaway:** metadata organizes memories. Know where each filter runs.
