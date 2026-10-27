-- The keyspace for the shop's memories: 3 replicas of every row, one per node.
-- mem0 would create the keyspace itself, but with the cluster's default replication.
-- Creating it first lets us choose replication explicitly.
CREATE KEYSPACE IF NOT EXISTS plushie_shop
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': 3}
  AND tablets = {'enabled': true};
