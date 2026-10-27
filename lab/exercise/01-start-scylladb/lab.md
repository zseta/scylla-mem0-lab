# 01 · Start the ScyllaDB cluster

mem0 needs a place to keep memories. You start a 3-node ScyllaDB cluster plus the **Vector Store** service that powers vector search.

- **ScyllaDB** (`scylladb/scylla:2026.3.4`) stores the memories: text, metadata and embedding vectors.
- **Vector Store** (`scylladb/vector-store:1.14.0`) keeps the vector indexes in memory. It follows table changes through CDC and answers the approximate nearest neighbor (ANN) part of a query.
- Each node runs in its own **rack** (`rack1`, `rack2`, `rack3`), like three availability zones. With replication factor 3, every rack holds a full copy of the data.

The nodes are deliberately small (`--smp 1 --memory 1G`), so the whole cluster fits on this lab VM.

## Do

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

## What happened

- `docker-compose.yml` starts `scylla-1`, then `scylla-2` and `scylla-3` join the cluster through the seed node.
- Every node points to the Vector Store (`--vector-store-primary-uri`), so any node can serve vector queries.
- ScyllaDB uses a shard-per-core design: each CPU core owns a slice of the data. A token-aware, shard-aware driver sends each request straight to a replica and the core that owns the row. Here each node has one core. In production you run bigger nodes.

**Takeaway:** the database is up, with 3 replicas across 3 racks. The bot does not use it yet.
