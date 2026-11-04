---
slug: workshop
id: nn9yqtiktt8y
type: challenge
title: Agent memory with mem0 and ScyllaDB
teaser: From a bot with no memory to a highly available memory layer, in 9 exercises.
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
- type: service
  title: Monitoring
  hostname: scylladb
  port: 3000
- id: 3h00xrh82pug
  title: Code
  type: code
  hostname: scylladb
  path: /root/mem0-lab/lab
difficulty: ""
timelimit: 7200
enhanced_loading: null
---

Welcome! In this lab you give an AI support bot a memory with **mem0**, stored in **ScyllaDB**.

You start with a bot that forgets everything between tickets. In each exercise you run one command and add one mem0 feature. You also see the CQL that mem0 sends to ScyllaDB, and what ScyllaDB does with it.

**Tabs**

- [**Terminal**](tab-0): run the commands. Use [**Terminal 2**](tab-1) when one command keeps running.
- [**App**](tab-2): the bot (Streamlit). Reload this tab after each `./run.sh`.
- [**Monitoring**](tab-3): ScyllaDB Monitoring (Grafana). Starts in exercise 01.

**Each exercise**

1. `cd` into the exercise folder and run `./run.sh`.
2. Open the [**App**](tab-2) tab and click **▶ Play scenario**, then **Next ▶** for each message. Or chat yourself.
3. Read **Under the hood** on the right: each step of a turn, with its CQL and latency.

You need a Gemini API key. Get one for free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Playing every scenario once uses about 30 Gemini calls (about 130k tokens). Each message you type adds 2 calls.

---

## 00 · Run the support bot (no memory)

Meet **plushie-bot**, the support bot of the ScyllaDB Plushie Shop. It runs on Gemini and answers questions about orders, shipping and returns.

It has no memory. Each reply sees only the messages of the current ticket. When the customer opens a new ticket, the bot starts from zero. That is the problem this workshop solves.

### Exercise

1. [**Terminal**](tab-0): start the bot. It asks for your Gemini API key the first time ([get one here](https://aistudio.google.com/apikey)).

   ```run,sh
   cd ~/mem0-lab/lab/exercise/00-run-the-bot && ./run.sh
   ```

2. [**App**](tab-2): click **▶ Play scenario**, then **Next ▶** for each message. The line above the chat shows who sends what next. Nora reports a late order, then opens a new ticket and asks for news.
3. [**App**](tab-2): read the reply in the new ticket. The bot asks for the order number again.
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

### Exercise

1. [**Terminal**](tab-0): start the cluster.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/01-start-scylladb && ./run.sh
   ```

2. [**Terminal**](tab-0): check that all three nodes show `UN` (Up, Normal), each in a different rack.

   ```run,sh
   docker exec scylla-1 nodetool status
   ```

   Want to explore further? `~/mem0-lab/lab/cqlsh.sh` opens an interactive CQL shell. Type `exit` to leave.

3. [**Monitoring**](tab-3): reload. The **Overview** dashboard shows 3 nodes. You come back here in exercise 08.

### What happened

- `docker-compose.yml` starts `scylla-1`, then `scylla-2` and `scylla-3` join the cluster through the seed node.
- Every node points to the Vector Store (`--vector-store-primary-uri`), so any node can serve vector queries.
- `run.sh` also starts [ScyllaDB Monitoring](https://monitoring.docs.scylladb.com/): Prometheus reads each node's metrics (port 9180) every 5 seconds, and Grafana shows them.
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

### Exercise

1. [**Terminal**](tab-0): create the keyspace, connect mem0, and print every CQL statement it runs.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/02-connect-mem0 && ./run.sh
   ```

2. [**Terminal**](tab-0): inspect the schema mem0 created.

   ```run,sh
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

CREATE TABLE plushie_shop.memories_entities (
  id text PRIMARY KEY,
  vector VECTOR<FLOAT, 384>,              -- the embedding of the entity text
  user_id text, agent_id text, run_id text,
  payload text                            -- JSON: entity text and type, linked_memory_ids
);
```

| Column | Type | In `memories` | In `memories_entities` |
|---|---|---|---|
| `id` | `text`, primary key | memory id (UUID) | entity id (UUID) |
| `vector` | `VECTOR<FLOAT, 384>` | embedding of the memory text | embedding of the entity text |
| `user_id` | `text` | the customer | the customer |
| `agent_id` | `text` | the bot | the bot |
| `run_id` | `text` | the ticket | the ticket |
| `payload` | `text` (JSON) | memory text, metadata, timestamps | entity text and type, `linked_memory_ids` |

An entity is a name or topic that mem0 finds in a memory (with spaCy, not the LLM), for example `Nora`, `Oslo` or `gift wrapping`. Each entity row points to the memories that mention it. `search()` looks up the entities of the question too, and ranks their linked memories higher.

On both tables, for each of `user_id`, `agent_id` and `run_id`, it creates two indexes:

```sql
-- vector index, scoped by user_id: ANN search only looks at one user's vectors
CREATE CUSTOM INDEX memories_user_id_ann ON plushie_shop.memories ((user_id), vector, agent_id, run_id)
  USING 'vector_index' WITH OPTIONS = {'similarity_function': 'COSINE'};
-- secondary index, for listing a user's memories
CREATE INDEX memories_user_id_idx ON plushie_shop.memories (user_id);
```

The 6 indexes on `memories`. `memories_entities` gets the same 6, named `memories_entities_*`.

| Index | Kind | Columns | Used by |
|---|---|---|---|
| `memories_user_id_ann` | local vector index | `(user_id)`, `vector`, filters `agent_id`, `run_id` | `search()` for one customer |
| `memories_agent_id_ann` | local vector index | `(agent_id)`, `vector`, filters `user_id`, `run_id` | `search()` for one bot |
| `memories_run_id_ann` | local vector index | `(run_id)`, `vector`, filters `user_id`, `agent_id` | `search()` for one ticket |
| `memories_user_id_idx` | secondary index | `user_id` | `get_all()` for one customer |
| `memories_agent_id_idx` | secondary index | `agent_id` | `get_all()` for one bot |
| `memories_run_id_idx` | secondary index | `run_id` | `get_all()` for one ticket |

- `((user_id), vector, ...)` is a **local vector index**: one small index per user, not one big global index. A search for Nora never ranks Erik's memories.
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

1. **Look up**: one vector search finds the 10 stored memories closest to the exchange.
2. **Extract**: one Gemini call turns the exchange into short facts, for example "User prefers email communication". It sees those 10 memories, so it skips facts that are already stored.
3. **Embed**: bge-small turns each fact into a 384-dimension vector, on CPU.
4. **Store**: it writes each fact to ScyllaDB, and links the entities (people, places, products) in `memories_entities`.

mem0 v3 only **adds**. It never silently overwrites an old fact.

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/03-add-memories && ./run.sh
   ```

2. [**App**](tab-2): reload the tab, then click **▶ Play scenario**. Nora sends her first message.
3. [**App**](tab-2): in **Under the hood**, read the `mem0.add` step: the facts mem0 extracted, then the CQL. The `SELECT ... ANN OF` on `memories` is the lookup, then one `INSERT` per new fact. The statements on `memories_entities` link the entities.
4. [**App**](tab-2): click **Next ▶** twice. In the new ticket, the bot still forgets: it writes memories but does not read them yet. That last message has no new facts, so `mem0.add` runs only the lookup.
5. [**Terminal**](tab-0): look at Nora's memories in ScyllaDB.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT id, payload FROM memories WHERE user_id = 'nora';"
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories_entities WHERE user_id = 'nora';"
   ```

### Under the hood

```sql
INSERT INTO plushie_shop.memories (id, vector, user_id, agent_id, run_id, payload)
VALUES (?, ?, ?, ?, ?, ?);
```

**Takeaway:** memories are short facts plus vectors, stored per customer.

---

## 04 · Read memories with `search()`

Before it answers, the bot asks mem0 what it knows about the customer and puts the results into the prompt:

```python
found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=10)["results"]
reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)
```

This is the standard memory loop: **search → prompt → LLM → add**.

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/04-search-memories && ./run.sh
   ```

2. [**App**](tab-2): reload, then click **▶ Play scenario**. Nora opens a new ticket and asks for news, like at the end of exercise 03.
3. [**App**](tab-2): this time the bot knows her order number and that she wants email. Open the `mem0.search` step: these are the memories exercise 03 stored.
4. [**App**](tab-2): click **Next ▶**. Erik asks what he ordered. The bot knows nothing about Erik: search only looks at Erik's memories.
5. [**App**](tab-2): in **Under the hood**, compare the `mem0.search` time with the `Gemini: reply` time.

### Under the hood

```sql
SELECT id, similarity_cosine(vector, ?) AS score, payload
FROM plushie_shop.memories
WHERE user_id = ?
ORDER BY vector ANN OF ?
LIMIT 10;
```

- `ORDER BY vector ANN OF ?` is an approximate nearest neighbor search: the Vector Store returns the closest vectors, and ScyllaDB returns the rows.
- `WHERE user_id = ?` uses the local vector index for that user, so the search covers only this customer's memories. It stays fast however many customers you have.
- `search()` time = embedding the question on CPU + this one query. The query itself takes a few milliseconds.
- A new memory becomes searchable about a second after `add()`: the Vector Store follows table changes through CDC. If you click **Next ▶** quickly, the scenario waits a moment for this.
- mem0 v3 can also rank by keywords (BM25). The ScyllaDB provider does not support that yet: search here is semantic only. ScyllaDB will cover mem0's hybrid search needs in the future.

**Takeaway:** the bot remembers across tickets, and each customer only sees their own memories.

---

## 05 · Memory lifecycle: update, delete, history

mem0 v3 only adds memories. When a fact changes ("I moved to Lisbon"), the old fact ("lives in Berlin") stays and both come back in search. Keeping memories correct is the application's job:

| Call | Use |
|---|---|
| `get_all(filters={"user_id": ...})` | list a customer's memories |
| `update(memory_id, text=...)` | correct one memory |
| `delete(memory_id)` | remove one memory |
| `history(memory_id)` | see how a memory changed |
| `delete_all(user_id=...)` | forget a customer completely |

This exercise adds a **Rep dashboard** tab for a human support rep. From here on, `add()` also records the bot (`agent_id`) and the ticket (`run_id`). `search()` still looks only at the customer's memories (`user_id`).

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/05-memory-lifecycle && ./run.sh
   ```

2. [**App**](tab-2): reload, then click **▶ Play scenario**. Nora moves to Lisbon, then asks where her next order ships. Open the `mem0.search` step: Berlin and Lisbon both come back.
3. [**App**](tab-2): open **Rep dashboard** (customer `nora`):
   - **Delete** what is wrong: every memory that puts her address in Berlin. Keep the order #4821 memories.
   - **Delete** duplicates, such as a second "User's name is Nora".
   - **Edit** one memory, then click **History** on it.
4. [**App**](tab-2): back in **Chat**, open a **New ticket** and ask *Which address will you ship my next order to?*
5. Optional: select `erik`, tick the checkbox, and click **Forget erik · delete_all()**.

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
- `add()` looks for duplicates only inside the scope it writes to. With `run_id` set, every new ticket starts from zero, so facts like "User's name is Nora" are stored again.
- `history()` shows **no CQL**: mem0 keeps history in a local SQLite file, not in ScyllaDB.

**Takeaway:** memory needs maintenance. Give people tools to fix and forget.

---

## 06 · Metadata and filters

Tag memories with your own fields when you add them, then filter on those fields when you search:

```python
memory.add(messages, user_id=customer, agent_id=bot, run_id=ticket,
           metadata={"category": "billing", "order_id": "4821"})

memory.search(text, filters={"user_id": customer, "category": "billing"})
```

The bot sets `category` from the ticket category in the sidebar, and `order_id` when the message mentions `#1234`.

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/06-metadata && ./run.sh
   ```

2. [**App**](tab-2): reload, then click **▶ Play scenario**:
   - a **billing** ticket: Nora was charged twice,
   - a **product** ticket: is the plushie washable,
   - a **billing** ticket with **Search only this category** on: only billing memories come back.
3. [**App**](tab-2): turn the filter off and on, and ask the same question. Compare the `mem0.search` results.
4. [**Terminal**](tab-0): see where the metadata lives.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'nora';" | grep category
   ```

### Under the hood

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

---

## 07 · Custom instructions: control what is remembered

By default mem0 keeps every fact that looks useful. That can include a phone number or a health condition. **Custom instructions** tell the extraction step what to keep and what to drop.

Set them once for every `add()`:

```python
Memory.from_config({..., "custom_instructions": PRIVACY_INSTRUCTIONS})
```

or per call, as this bot does:

```python
memory.add(messages, user_id=customer, prompt=PRIVACY_INSTRUCTIONS)
```

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/07-custom-instructions && ./run.sh
   ```

2. [**App**](tab-2): reload, then click **▶ Play scenario**. Erik sends an order with his phone number and a wool allergy. Privacy instructions are OFF.
   - Open the `mem0.add` step. The wool allergy (health data) is stored, often the phone number too.
3. [**App**](tab-2): click **Next ▶**. Nora sends the same message. Privacy instructions are ON.
   - Open the `mem0.add` step. Only the order is stored.
4. [**App**](tab-2): read Erik's facts once more. One of them is something the **bot** said, for example "User was informed that the plushie is wool-free". mem0 remembers the bot's words too, right or wrong.
5. [**Terminal**](tab-0): compare what ScyllaDB holds for Erik and for Nora. Nora's memories from earlier exercises are there too, but no allergy and no phone number.

   ```run,sh
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'erik';"
   ~/mem0-lab/lab/cqlsh.sh -e "SELECT payload FROM memories WHERE user_id = 'nora';"
   ```

### Under the hood

- Custom instructions change only the extraction prompt, so they cost no extra calls.
- Fewer facts means fewer `INSERT`s in ScyllaDB. Compare the CQL count of the two `mem0.add` steps.
- `add()` extracts facts from **both** the customer and the bot. If the bot invents something, it can end up in memory. Instructions like "only remember what the customer states" help.

**Takeaway:** data you never store cannot leak. Decide what memory is for.

---

## 08 · High availability: lose a node, keep the memory

The keyspace has 3 replicas of every row, one per rack. This bot reads and writes at **QUORUM**: 2 of the 3 replicas must answer. With one node down, 2 replicas still answer, so nothing fails.

```python
from cassandra import ConsistencyLevel
set_consistency(memory, ConsistencyLevel.QUORUM)   # every mem0 read and write
```

### Exercise

1. [**Terminal**](tab-0): start this exercise's bot. The sidebar shows each node's status.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/08-high-availability && ./run.sh
   ```

2. [**Terminal**](tab-0): start the health check. Every second it writes a memory and reads it back at QUORUM. Leave it running.

   ```run,sh
   ~/mem0-lab/lab/exercise/08-high-availability/ha_check.sh
   ```

3. [**Terminal 2**](tab-1): stop one node.

   ```run,sh
   docker stop scylla-3
   docker exec scylla-1 nodetool status
   ```

4. [**Terminal**](tab-0): watch the health check: `nodes up: 2/3`, and every line still says `OK`.
5. [**Monitoring**](tab-3): within about 10 seconds, the **Overview** dashboard shows a red **Unreachable Nodes** box and **Unreachable 1**. Reads and writes from the health check continue.
6. [**App**](tab-2): reload, then click **▶ Play scenario**. With `scylla-3` down, the bot reads Nora's address, stores a delivery note, and finds it again in a new ticket. Click **Refresh status** to see `scylla-3` down.
7. [**Terminal 2**](tab-1): bring the node back. It rejoins and catches up on the writes it missed.

   ```run,sh
   docker start scylla-3
   ```

8. [**Monitoring**](tab-3): open the **Detailed** dashboard and scroll to **Hints Written**. It rose while `scylla-3` was down: the other nodes saved its writes as hints. **Hints sent** spikes when it comes back and receives them.

### Under the hood

- **Replication factor 3** + **3 racks**: one copy per rack. Losing a node, or a whole availability zone in production, loses no data.
- **QUORUM** keeps reads consistent: any 2 replicas overlap with the 2 that acknowledged the last write.
- When the node returns, **hinted handoff** and **repair** bring it up to date.
- In this lab the **Vector Store** is a single container, so don't stop it. In ScyllaDB Cloud the Vector Store nodes are replicated across zones too.
- mem0's history is a local SQLite file on the app host. It does not get ScyllaDB's replication.

**Takeaway:** agent memory is production data. Store it in a database that survives failures.
