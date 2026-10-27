#!/usr/bin/env bash
# Exercise 01: start a 3-node ScyllaDB cluster plus the Vector Store service.
set -euo pipefail
cd "$(dirname "$0")"

echo "Starting scylla-1, scylla-2, scylla-3 and the Vector Store (about 1 minute)..."
docker compose up -d --wait

echo
echo "Cluster status (UN = Up and Normal):"
docker exec scylla-1 nodetool status
echo
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' --filter name=scylla- --filter name=lab-vector-store
