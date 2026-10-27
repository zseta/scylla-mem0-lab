# 02 · Connect mem0 to ScyllaDB

mem0 is a memory layer for AI agents. It has three parts, all set in one config:

| Part | This lab uses | Job |
|---|---|---|
| LLM | Gemini `gemini-3.5-flash-lite` | extracts facts from conversations |
| Embedder | `BAAI/bge-small-en-v1.5` on CPU, 384 dimensions | turns text into vectors |
| Vector store | ScyllaDB (`provider: "scylladb"`) | stores and searches memories |

mem0, with its ScyllaDB provider, is already installed in this lab.

## Do

1. **Terminal**: create the keyspace, connect mem0, and print every CQL statement it runs.

   ```bash
   cd ~/mem0-lab/lab/exercise/02-connect-mem0 && ./run.sh
   ```

2. **Terminal**: inspect the schema mem0 created.

   ```bash
   ~/mem0-lab/lab/cqlsh.sh -e "DESCRIBE TABLE plushie_shop.memories"
   ```

## Under the hood

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
