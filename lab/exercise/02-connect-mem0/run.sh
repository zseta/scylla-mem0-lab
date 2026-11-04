#!/usr/bin/env bash
# Exercise 02: create the keyspace (RF=3), then let mem0 create its tables and indexes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"

echo "Creating keyspace plushie_shop with replication factor 3..."
docker exec -i scylla-1 cqlsh < "$HERE/keyspace.cql"
echo

mkdir -p "$LAB_DIR/.data"
cd "$HERE"
# A fresh cluster can be slow with schema changes and time out. Every statement is IF NOT EXISTS, so retry.
for attempt in 1 2 3; do
  if PYTHONPATH="$LAB_DIR" uv run --project "$LAB_DIR" --quiet python connect.py 2> "$LAB_DIR/.data/connect.log"; then
    exit 0
  fi
  grep -q OperationTimedOut "$LAB_DIR/.data/connect.log" && [ "$attempt" -lt 3 ] || break
  echo "ScyllaDB is still busy with the schema changes. Retrying..."
done
tail -20 "$LAB_DIR/.data/connect.log"
exit 1
