#!/usr/bin/env bash
# Exercise 02: create the keyspace (RF=3), then let mem0 create its tables and indexes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"

echo "Creating keyspace plushie_shop with replication factor 3..."
docker exec -i scylla-1 cqlsh < "$HERE/keyspace.cql"
echo

cd "$HERE"
PYTHONPATH="$LAB_DIR" uv run --project "$LAB_DIR" --quiet python connect.py 2> "$LAB_DIR/.data/connect.log" \
  || { tail -20 "$LAB_DIR/.data/connect.log"; exit 1; }
