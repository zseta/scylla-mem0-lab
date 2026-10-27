# 07 · Metadata and filters

Tag memories with your own fields when you add them, then filter on those fields when you search:

```python
memory.add(messages, user_id=customer, agent_id=bot, run_id=ticket,
           metadata={"category": "billing", "order_id": "4821"})

memory.search(text, filters={"user_id": customer, "category": "billing"})
```

The bot sets `category` from the ticket category in the sidebar, and `order_id` when the message mentions `#1234`.

## Do

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/07-metadata && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**:
   - a **billing** ticket: Alice was charged twice,
   - a **product** ticket: is the plushie washable,
   - a **billing** ticket with **Search only this category** on: only billing memories come back.
3. **App**: turn the filter off and on, and ask the same question. Compare the `mem0.search` results.
4. **Terminal**: see where the metadata lives.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'alice';" | grep category
   ```

## Under the hood

- Metadata is stored inside the `payload` JSON column, not in its own column.
- `user_id`, `agent_id` and `run_id` filters run **in ScyllaDB**, inside the vector query.
- Metadata filters run **in the app**, on the rows ScyllaDB returns. If filtering removes too many rows, the provider asks again with a bigger `LIMIT` (×4 each time).

```sql
SELECT ... WHERE user_id = ? ORDER BY vector ANN OF ? LIMIT 5;   -- then LIMIT 20, 80, ...
```

**Design lesson:** a field you filter on all the time belongs in a real column, so the database can filter on it.

**Takeaway:** metadata organizes memories. Know where each filter runs.
