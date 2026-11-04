-- The keyspace for the shop's memories: 3 replicas of every row, one per node.
-- mem0 creates the keyspace itself if it is missing, with the cluster's default replication.
-- Create it yourself first when you want to customize it (replication factor, datacenters, tablets).
CREATE KEYSPACE IF NOT EXISTS plushie_shop
  WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': 3}
  AND tablets = {'enabled': true};
