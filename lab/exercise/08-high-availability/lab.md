# 08 · High availability: lose a node, keep the memory

The keyspace has 3 replicas of every row, one per rack. This bot reads and writes at **QUORUM**: 2 of the 3 replicas must answer. With one node down, 2 replicas still answer, so nothing fails.

```python
from cassandra import ConsistencyLevel
set_consistency(memory, ConsistencyLevel.QUORUM)   # every mem0 read and write
```

## Exercise

1. **Terminal**: start this exercise's bot. The sidebar shows each node's status.

   ```run,sh
   cd ~/mem0-lab/lab/exercise/08-high-availability && ./run.sh
   ```

2. **Terminal**: start the health check. Every second it writes a memory and reads it back at QUORUM. Leave it running.

   ```run,sh
   ~/mem0-lab/lab/exercise/08-high-availability/ha_check.sh
   ```

3. **Terminal 2**: stop one node.

   ```run,sh
   docker stop scylla-3
   docker exec scylla-1 nodetool status
   ```

4. **Terminal**: watch the health check: `nodes up: 2/3`, and every line still says `OK`.
5. **Monitoring**: within about 10 seconds, the **Overview** dashboard shows a red **Unreachable Nodes** box and **Unreachable 1**. Reads and writes from the health check continue.
6. **App**: reload, then click **▶ Play scenario**. With `scylla-3` down, the bot reads Nora's address, stores a delivery note, and finds it again in a new ticket. Click **Refresh status** to see `scylla-3` down.
7. **Terminal 2**: bring the node back. It rejoins and catches up on the writes it missed.

   ```run,sh
   docker start scylla-3
   ```

8. **Monitoring**: open the **Detailed** dashboard and scroll to **Hints Written**. It rose while `scylla-3` was down: the other nodes saved its writes as hints. **Hints sent** spikes when it comes back and receives them.

## Under the hood

- **Replication factor 3** + **3 racks**: one copy per rack. Losing a node, or a whole availability zone in production, loses no data.
- **QUORUM** keeps reads consistent: any 2 replicas overlap with the 2 that acknowledged the last write.
- When the node returns, **hinted handoff** and **repair** bring it up to date.
- In this lab the **Vector Store** is a single container, so don't stop it. In ScyllaDB Cloud the Vector Store nodes are replicated across zones too.
- mem0's history is a local SQLite file on the app host. It does not get ScyllaDB's replication.

**Takeaway:** agent memory is production data. Store it in a database that survives failures.
