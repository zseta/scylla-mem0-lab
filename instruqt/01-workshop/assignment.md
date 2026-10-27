---
slug: workshop
id: nn9yqtiktt8y
type: challenge
title: Agent memory with mem0 and ScyllaDB
teaser: From a bot with no memory to a highly available memory layer, in 11 exercises.
tabs:
- id: b7ledbdcrp9t
  title: Terminal
  type: terminal
  hostname: scylladb
  workdir: /root/mem0-lab/lab
- id: m5wmeupaooic
  title: Terminal 2
  type: terminal
  hostname: scylladb
  workdir: /root/mem0-lab/lab
- id: v9xxznibfxbj
  title: App
  type: service
  hostname: scylladb
  port: 8501
difficulty: ""
timelimit: 7200
enhanced_loading: null
---

Welcome! In this lab you give an AI support bot a memory with **mem0**, stored in **ScyllaDB**.

You start with a bot that forgets everything between tickets. In each exercise you run one command and add one mem0 feature. You also see the CQL that mem0 sends to ScyllaDB, and what ScyllaDB does with it.

**Tabs**

- **Terminal**: run the commands. Use **Terminal 2** when one command keeps running.
- **App**: the bot (Streamlit). Reload this tab after each `./run.sh`.

**Each exercise**

1. `cd` into the exercise folder and run `./run.sh`.
2. Open the **App** tab and click **▶ Play scenario**, or chat yourself.
3. Read **Under the hood** on the right: each step of a turn, with its CQL and latency.

You need a Gemini API key. Get one for free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Playing every scenario once uses about 45 Gemini calls (about 170k tokens). Each message you type adds 2 calls.

---

## 00 · Run the support bot (no memory)

Meet **plushie-bot**, the support bot of the ScyllaDB Plushie Shop. It runs on Gemini and answers questions about orders, shipping and returns.

It has no memory. Each reply sees only the messages of the current ticket. When the customer opens a new ticket, the bot starts from zero. That is the problem this workshop solves.

### Do

1. **Terminal**: start the bot. It asks for your Gemini API key the first time ([get one here](https://aistudio.google.com/apikey)).

   ```bash
   cd ~/mem0-lab/lab/exercise/00-run-the-bot && ./run.sh
   ```

2. **App**: click **▶ Play scenario**. Alice reports a late order, then opens a new ticket and asks for news.
3. **App**: read the reply in the new ticket. The bot asks for the order number again.
4. Optional: write your own messages. Click **New ticket** in the sidebar to start a fresh conversation.

### What happened

- Every turn sends one prompt to Gemini: the system prompt plus the messages of this ticket.
- The **Under the hood** panel shows one step per turn: `Gemini: reply`. No database is involved yet.
- The sidebar counts Gemini calls and tokens, so you can keep an eye on your quota.

**Takeaway:** chat history is not memory. The next exercises give the bot a memory that outlives the ticket.

---

## 01 · Start the ScyllaDB cluster

mem0 needs a place to keep memories. You start a 3-node ScyllaDB cluster plus the **Vector Store** service that powers vector search.

- **ScyllaDB** (`scylladb/scylla:2026.3.4`) stores the memories: text, metadata and embedding vectors.
- **Vector Store** (`scylladb/vector-store:1.14.0`) keeps the vector indexes in memory. It follows table changes through CDC and answers the approximate nearest neighbor (ANN) part of a query.
- Each node runs in its own **rack** (`rack1`, `rack2`, `rack3`), like three availability zones. With replication factor 3, every rack holds a full copy of the data.

The nodes are deliberately small (`--smp 1 --memory 1G`), so the whole cluster fits on this lab VM.

### Do

1. **Terminal**: start the cluster (about 1 minute).

   ```bash
   cd ~/mem0-lab/lab/exercise/01-start-scylladb && ./run.sh
   ```

2. **Terminal**: check that all three nodes show `UN` (Up, Normal), each in a different rack.

   ```bash
   docker exec scylla-1 nodetool status
   ```

3. **Terminal**: open a CQL shell and look around. Type `exit` to leave.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh
   ```

   ```sql
   SELECT host_id, rack FROM system.local;
   SELECT peer, rack FROM system.peers;
   ```

### What happened

- `docker-compose.yml` starts `scylla-1`, then `scylla-2` and `scylla-3` join the cluster through the seed node.
- Every node points to the Vector Store (`--vector-store-primary-uri`), so any node can serve vector queries.
- ScyllaDB uses a shard-per-core design: each CPU core owns a slice of the data. A token-aware, shard-aware driver sends each request straight to a replica and the core that owns the row. Here each node has one core. In production you run bigger nodes.

**Takeaway:** the database is up, with 3 replicas across 3 racks. The bot does not use it yet.

---

## 02 · Connect mem0 to ScyllaDB

mem0 is a memory layer for AI agents. It has three parts, all set in one config:

| Part | This lab uses | Job |
|---|---|---|
| LLM | Gemini `gemini-3.5-flash-lite` | extracts facts from conversations |
| Embedder | `BAAI/bge-small-en-v1.5` on CPU, 384 dimensions | turns text into vectors |
| Vector store | ScyllaDB (`provider: "scylladb"`) | stores and searches memories |

mem0, with its ScyllaDB provider, is already installed in this lab.

### Do

1. **Terminal**: create the keyspace, connect mem0, and print every CQL statement it runs.

   ```bash
   cd ~/mem0-lab/lab/exercise/02-connect-mem0 && ./run.sh
   ```

2. **Terminal**: inspect the schema mem0 created.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "DESCRIBE TABLE plushie_shop.memories"
   ```

### Under the hood

`keyspace.cql` creates the keyspace first, with 3 replicas:

```sql
CREATE KEYSPACE IF NOT EXISTS plushie_shop
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': 3}
  AND tablets = {'enabled': true};
```

Then mem0 creates one table for memories and one for the entities it extracts:

```sql
CREATE TABLE plushie_shop.memories (
  id text PRIMARY KEY,
  vector VECTOR<FLOAT, 384>,              -- the embedding
  user_id text, agent_id text, run_id text, -- who the memory belongs to
  payload text                            -- JSON: memory text, metadata, timestamps
);
```

For each of `user_id`, `agent_id` and `run_id`, it creates two indexes:

```sql
-- vector index, scoped by user_id: ANN search only looks at one user's vectors
CREATE CUSTOM INDEX memories_user_id_ann ON plushie_shop.memories ((user_id), vector, agent_id, run_id)
  USING 'vector_index' WITH OPTIONS = {'similarity_function': 'COSINE'};
-- secondary index, for listing a user's memories
CREATE INDEX memories_user_id_idx ON plushie_shop.memories (user_id);
```

- `((user_id), vector, ...)` is a **local vector index**: one small index per user, not one big global index. A search for Alice never ranks Bob's memories.
- Indexes need a keyspace that is **RF-rack-valid**: the replication factor equals the number of racks. That is why the cluster has 3 racks.
- mem0 keeps the change history of each memory in a local SQLite file (`lab/.data/history.db`), not in ScyllaDB.

**Takeaway:** mem0 manages the schema. You choose the replication.

---

## 03 · Write memories with `add()`

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

### Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/03-add-memories && ./run.sh
   ```

2. **App**: reload the tab, then click **▶ Play scenario**.
3. **App**: in **Under the hood**, open the `mem0.add` step. You see the stored facts and the `INSERT` statements.
4. **App**: in the new ticket, the bot still forgets. It writes memories but does not read them yet.
5. **Terminal**: look at Alice's memories in ScyllaDB.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT id, payload FROM memories WHERE user_id = 'alice';"
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories_entities WHERE user_id = 'alice';"
   ```

### Under the hood

```sql
INSERT INTO plushie_shop.memories (id, vector, user_id, agent_id, run_id, payload)
VALUES (?, ?, ?, ?, ?, ?);
```

- Every write goes to all 3 replicas. The commitlog makes it durable before ScyllaDB acknowledges it.
- About 1 second of `add()` is the Gemini call. The database part takes a few milliseconds.

**Takeaway:** memories are short facts plus vectors, stored per customer.

---

## 04 · Read memories with `search()`

Before it answers, the bot asks mem0 what it knows about the customer and puts the results into the prompt:

```python
found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=5)["results"]
reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)
```

This is the standard memory loop: **search → prompt → LLM → add**.

### Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/04-search-memories && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**.
3. **App**: in Alice's new ticket, the bot now remembers the order, the city and the email preference.
4. **App**: Bob asks what he ordered. The bot knows nothing about Bob: search only looks at Bob's memories.
5. **App**: in **Under the hood**, compare the `mem0.search` time with the `Gemini: reply` time.

### Under the hood

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

---

## 05 · Scope memories: customer, bot, ticket

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

### Do

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

### Under the hood

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

---

## 06 · Memory lifecycle: update, delete, history

mem0 v3 only adds memories. When a fact changes ("I moved to Lisbon"), the old fact ("lives in Berlin") stays and both come back in search. Keeping memories correct is the application's job:

| Call | Use |
|---|---|
| `get_all(filters={"user_id": ...})` | list a customer's memories |
| `update(memory_id, text=...)` | correct one memory |
| `delete(memory_id)` | remove one memory |
| `history(memory_id)` | see how a memory changed |
| `delete_all(user_id=...)` | forget a customer completely |

This exercise adds a **Rep dashboard** tab for a human support rep.

### Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/06-memory-lifecycle && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. Alice moves to Lisbon, then asks where her next order ships. The bot sees Berlin, Oslo and Lisbon.
3. **App**: open **Rep dashboard** (customer `alice`):
   - **Delete** the memories about Berlin and the Oslo office, and the leaked "User's name is Bob".
   - **Edit** one memory, then click **History** on it.
4. **App**: back in **Chat**, open a **New ticket** and ask *Which address will you ship my next order to?*
5. Optional: select `bob`, tick the checkbox, and click **Forget bob · delete_all()**.

### Under the hood

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
- `history()` shows **no CQL**: mem0 keeps history in a local SQLite file, not in ScyllaDB.

**Takeaway:** memory needs maintenance. Give people tools to fix and forget.

---

## 07 · Metadata and filters

Tag memories with your own fields when you add them, then filter on those fields when you search:

```python
memory.add(messages, user_id=customer, agent_id=bot, run_id=ticket,
           metadata={"category": "billing", "order_id": "4821"})

memory.search(text, filters={"user_id": customer, "category": "billing"})
```

The bot sets `category` from the ticket category in the sidebar, and `order_id` when the message mentions `#1234`.

### Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/07-metadata && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**:
   - a **billing** ticket: Alice was charged twice,
   - a **product** ticket: is the plushie washable,
   - a **billing** ticket with **Search only this category** on: only billing memories come back.
3. **App**: turn the filter off and on, and ask the same question. Compare the `mem0.search` results.
4. **Terminal**: see where the metadata lives.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'alice';" | grep category
   ```

### Under the hood

- Metadata is stored inside the `payload` JSON column, not in its own column.
- `user_id`, `agent_id` and `run_id` filters run **in ScyllaDB**, inside the vector query.
- Metadata filters run **in the app**, on the rows ScyllaDB returns. If filtering removes too many rows, the provider asks again with a bigger `LIMIT` (×4 each time).

```sql
SELECT ... WHERE user_id = ? ORDER BY vector ANN OF ? LIMIT 5;   -- then LIMIT 20, 80, ...
```

**Design lesson:** a field you filter on all the time belongs in a real column, so the database can filter on it.

**Takeaway:** metadata organizes memories. Know where each filter runs.

---

## 08 · Custom instructions: control what is remembered

By default mem0 keeps every fact that looks useful. That can include a phone number, a health condition, even a card number. **Custom instructions** tell the extraction step what to keep and what to drop.

Set them once for every `add()`:

```python
Memory.from_config({..., "custom_instructions": PRIVACY_INSTRUCTIONS})
```

or per call, as this bot does:

```python
memory.add(messages, user_id=customer, prompt=PRIVACY_INSTRUCTIONS)
```

### Do

1. **Terminal**: start this exercise's bot.

   ```bash
   cd ~/mem0-lab/lab/exercise/08-custom-instructions && ./run.sh
   ```

2. **App**: reload, then click **▶ Play scenario**. Bob sends the same message twice: card number, phone number, wool allergy.
   - **Privacy instructions OFF**: open the `mem0.add` step. The phone number and the allergy are stored.
   - **Privacy instructions ON**: only the order is stored.
3. **App**: read the facts stored with privacy OFF once more. Did mem0 also store something the **bot** said, for example a product claim the bot made up?
4. **Terminal**: check what ScyllaDB holds for Bob.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'bob';"
   ```

### Under the hood

- Custom instructions change only the extraction prompt, so they cost no extra calls.
- Fewer facts means fewer `INSERT`s in ScyllaDB. Compare the CQL count of the two `mem0.add` steps.
- `add()` extracts facts from **both** the customer and the bot. If the bot invents something, it can end up in memory. Instructions like "only remember what the customer states" help.

**Takeaway:** data you never store cannot leak. Decide what memory is for.

---

## 09 · Performance and scale

> This lab VM is small, with 3 nodes on one machine and 1 CPU core each. The numbers show where time goes, not what production hardware does.

A memory turn has three costs:

| Step | Where the time goes | Customer waits? |
|---|---|---|
| `search()` | embed the question (CPU) + one ANN query | yes |
| LLM reply | Gemini | yes |
| `add()` | Gemini extraction + embed + writes | **no need** |

### Do

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

### What the numbers say

- The database is not the bottleneck. The ANN query is fast and steady.
- `mem0.search()` is slower because Python embeds each question on CPU and extracts entities with spaCy, and the threads compete for the CPU.

### Techniques for real scale

- **Keep `add()` off the hot path**: background workers or a queue.
- **Scale the app tier**: more processes or pods. Embedding is CPU work.
- **Faster embeddings**: GPU, a hosted embedding API, or batching.
- **Small `top_k`** (5–10): fewer rows, smaller prompts.
- **Choose embedding dimensions on purpose**: the size is fixed in the `VECTOR<FLOAT, N>` column.
- **Driver settings**: prepared statements (the provider uses them), `datacenter` set to the local DC, and token-aware routing (`TokenAwarePolicy`), so each request goes straight to a replica and the core that owns the row.
- **Bigger ScyllaDB nodes**: more cores means more shards. ScyllaDB Cloud scales nodes and the Vector Store for you.

**Takeaway:** measure each layer. Make the database the last thing you have to scale.

---

## 10 · High availability: lose a node, keep the memory

The keyspace has 3 replicas of every row, one per rack. This bot reads and writes at **QUORUM**: 2 of the 3 replicas must answer. With one node down, 2 replicas still answer, so nothing fails.

```python
from cassandra import ConsistencyLevel
set_consistency(memory, ConsistencyLevel.QUORUM)   # every mem0 read and write
```

### Do

1. **Terminal**: start this exercise's bot. The sidebar shows each node's status.

   ```bash
   cd ~/mem0-lab/lab/exercise/10-high-availability && ./run.sh
   ```

2. **Terminal**: start the health check. Every second it writes a memory and reads it back at QUORUM. Leave it running.

   ```bash
   ./ha_check.sh
   ```

3. **Terminal 2**: stop one node.

   ```bash
   docker stop scylla-3
   docker exec scylla-1 nodetool status
   ```

4. Watch the health check: `nodes up: 2/3`, and every line still says `OK`.
5. **App**: reload, click **▶ Play scenario**, then chat. The bot still remembers Alice. Click **Refresh status** to see `scylla-3` down.
6. **Terminal**: bring the node back. It rejoins and catches up on the writes it missed.

   ```bash
   docker start scylla-3
   ```

### Under the hood

- **Replication factor 3** + **3 racks**: one copy per rack. Losing a node, or a whole availability zone in production, loses no data.
- **QUORUM** keeps reads consistent: any 2 replicas overlap with the 2 that acknowledged the last write.
- When the node returns, **hinted handoff** and **repair** bring it up to date.
- In this lab the **Vector Store** is a single container, so don't stop it. In ScyllaDB Cloud the Vector Store nodes are replicated across zones too.
- mem0's history is a local SQLite file on the app host. It does not get ScyllaDB's replication.

**Takeaway:** agent memory is production data. Store it in a database that survives failures.
