# 04 · Read memories with `search()`

Before it answers, the bot asks mem0 what it knows about the customer and puts the results into the prompt:

```python
found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=5)["results"]
reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)
```

This is the standard memory loop: **search → prompt → LLM → add**.

## Do

1. **Terminal**: start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/04-search-memories && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**.
3. **App**: in Alice's new ticket, the bot now remembers the order, the city and the email preference.
4. **App**: Bob asks what he ordered. The bot knows nothing about Bob: search only looks at Bob's memories.
5. **App**: in **Under the hood**, compare the `mem0.search` time with the `Gemini: reply` time.

## Under the hood

```sql
SELECT id, similarity_cosine(vector, ?) AS score, payload
FROM plushie_shop.memories
WHERE user_id = ?
ORDER BY vector ANN OF ?
LIMIT 5;
```

- `ORDER BY vector ANN OF ?` is an approximate nearest neighbor search: the Vector Store returns the closest vectors, and ScyllaDB returns the rows.
- `WHERE user_id = ?` uses the local vector index for that user, so the search covers only this customer's memories. It stays fast however many customers you have.
- `search()` time = embedding the question on CPU + this one query. The query itself takes a few milliseconds.
- A new memory becomes searchable about a second after `add()`: the Vector Store follows table changes through CDC. The scenario pauses between steps for this.
- mem0 v3 can also rank by keywords (BM25). The ScyllaDB provider does not support that yet: search here is semantic only. ScyllaDB will cover mem0's hybrid search needs in the future.

**Takeaway:** the bot remembers across tickets, and each customer only sees their own memories.
