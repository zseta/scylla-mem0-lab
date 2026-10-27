# 05 · Scope memories: customer, bot, ticket

Real support has many customers, several bots and many tickets. mem0 tags every memory with up to three IDs:

| ID | In this shop | Example |
|---|---|---|
| `user_id` | the customer | `alice` |
| `agent_id` | the bot | `shipping-bot`, `billing-bot` |
| `run_id` | the ticket | `T-1004` |

`add()` stores all three. `search()` decides which scope to look in:

```python
memory.add(messages, user_id=customer, agent_id=bot, run_id=ticket)
memory.search(text, filters={"user_id": customer})
```

## Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/05-scoping && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**:
   - Bob gives the shipping bot his office address in Oslo.
   - Alice asks the shipping bot for her address, with scope **Bot only · agent_id**. The bot answers with **Bob's** address.
   - Alice asks again, with scope **Customer · user_id**. Now look at what she gets back.
3. **App**: in the sidebar, try each scope and ask: *Which address will you ship my order to?*
4. **Terminal**: the leaked answer was stored as Alice's memory. Find it:

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'alice';" | grep -i oslo
   ```

## Under the hood

One scope column uses that column's local vector index:

```sql
SELECT ... FROM plushie_shop.memories WHERE user_id = ? ORDER BY vector ANN OF ? LIMIT 5;
```

Two columns add `ALLOW FILTERING`. The filtering only runs inside one user's index:

```sql
SELECT ... WHERE user_id = ? AND agent_id = ? ORDER BY vector ANN OF ? LIMIT 5 ALLOW FILTERING;
```

- Scoping by `agent_id` alone searches everything that bot ever heard, from every customer.
- A wrong read becomes a wrong write: `add()` stored the leaked reply as a fact about Alice. Exercise 06 cleans it up.
- `search()` without any of the three IDs fails. mem0 and the ScyllaDB provider both require a scope.

**Takeaway:** always scope by `user_id`. Narrow with `agent_id` or `run_id` when it makes sense.
