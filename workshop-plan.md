# Workshop: Agent Memory with mem0 + ScyllaDB

**App:** customer support bot. Starts with no memory. Each exercise adds one mem0 feature.
**Per exercise:** app change → CQL under the hood → ScyllaDB point.
**Stack:** mem0 OSS (v3) + ScyllaDB provider ([PR #5373](https://github.com/mem0ai/mem0/pull/5373)) + 3-node ScyllaDB in Docker (vector search enabled).

---

## 0. Run the bot
- Clone repo, run bot. No memory, no DB.
- Show it forgetting the customer between tickets.

## 1. Start ScyllaDB
- `docker compose up`: 3-node cluster with vector search.
- `nodetool status`, `cqlsh`.
- **ScyllaDB:** shard-per-core, tablets, replication factor.

## 2. Install and connect mem0
- Install mem0 + ScyllaDB provider. `Memory.from_config(...)`.
- **CQL:** mem0 creates the schema:
  - `CREATE KEYSPACE`: no replication clause → NetworkTopologyStrategy + tablets, RF=3.
  - `CREATE TABLE memories (id, vector VECTOR<FLOAT,N>, user_id, agent_id, run_id, payload)`
  - 3 local vector indexes (`USING 'vector_index'`) + 3 secondary indexes.
  - `memories_entities` table (entity store).
- Inspect with `DESCRIBE`.
- **ScyllaDB:** one local vector index per customer.

## 3. `add()`: remember the customer
- **App change:** `add(messages, user_id=customer)` after each turn.
- **Under the hood:** LLM extracts facts → embed → `INSERT INTO memories ...` + entity inserts.
- `SELECT` the new rows in cqlsh.
- **ScyllaDB:** write path, commitlog durability, RF=3, shard-aware driver.

## 4. `search()`: look up the customer before answering
- **CQL:** `SELECT id, similarity_cosine(vector, ?) ... WHERE user_id = ? ORDER BY vector ANN OF ? LIMIT ?`
- `TRACING ON`.
- **ScyllaDB:** search covers only this customer's vectors. Latency does not grow with customer count.

## 5. Scoping: customer / bot / ticket
- **App change:** `user_id` = customer, `agent_id` = billing bot or shipping bot, `run_id` = ticket.
- **CQL:** scoping by two columns adds `ALLOW FILTERING`, limited to one customer's index. A search with no scope fails.
- **ScyllaDB:** tenant isolation comes from the index design.

## 6. Memory lifecycle
- **App change:** rep dashboard (`get_all`, `get`, `history`). Address change (`update`). "Forget me" (`delete_all`).
- **CQL:** `SELECT ... WHERE user_id = ?`, `UPDATE ... WHERE id = ?`, `DELETE ... WHERE id = ?`.
- **ScyllaDB:** tombstones. Index picks up changes through CDC in about 1s. `reset()` drops the table instead of running `TRUNCATE`.
- v3 add is ADD-only: changed facts are the app's job.

## 7. Metadata filters
- **App change:** tag ticket category and order ID, then filter on them.
- **Under the hood:** same ANN query. Payload filters run on the client. Provider re-fetches with LIMIT ×4 if filters remove too many results.
- **Design lesson:** fields you filter on a lot belong in real columns.

## 8. `custom_instructions` + entities
- **App change:** never store card numbers or phone numbers. Link products.
- Compare stored rows before and after.
- Data never stored cannot leak.

## 9. Performance and scale techniques
Workshop runs on small machines. Show techniques, not production numbers.
- Measure: search p50/p99 vs LLM time. The LLM dominates; search should be a few ms.
- Keep `add()` off the hot path: `AsyncMemory`, background queue.
- Shard-aware driver, prepared statements, DC-aware routing (`datacenter`).
- Small `top_k`. Pick embedding dims on purpose (fixed in the column type).
- Consistency level vs latency.
- Short load run with N concurrent customers.
- Production: bigger nodes, more nodes, ScyllaDB Cloud.

## 10. High availability
- `docker stop` one node mid-conversation. Bot keeps reading and writing memories.
- Restart the node and watch it catch up.
- **ScyllaDB:** RF=3, consistency levels, no single point of failure.

---

## Mention only (not exercises)
- **Hybrid (BM25) search:** mem0 v3 hybrid search needs keyword search with per-user filters. ScyllaDB will support this in the future, not yet.
- **Platform-only features:** Graph Memory, Profiles, Dream, webhooks.

## Open issues
- PR #5373 not merged → install from branch or a pinned fork.
- History is stored in local SQLite (`history_db_path`), not ScyllaDB. It does not survive host loss. Say so in exercise 10.
- Pin a ScyllaDB Docker image tag with vector search.
- Repo: one branch per exercise, so people who fall behind can catch up.
