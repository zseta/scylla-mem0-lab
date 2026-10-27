#!/usr/bin/env bash
# Start over: stop the app, delete all memories and their history.
# Keeps the cluster running. Run exercise 02 again afterwards.
# Add --all to also remove the cluster containers.
set -euo pipefail
LAB_DIR="$(cd "$(dirname "$0")" && pwd)"

pkill -f "streamlit run app.py" 2>/dev/null || true
rm -f "$LAB_DIR/.data/history.db"
if docker ps --format '{{.Names}}' | grep -qx scylla-1; then
  docker exec scylla-1 cqlsh -e "DROP KEYSPACE IF EXISTS plushie_shop"
  echo "Dropped keyspace plushie_shop."
fi
if [ "${1:-}" = "--all" ]; then
  docker compose -f "$LAB_DIR/exercise/01-start-scylladb/docker-compose.yml" down
fi
echo "Reset done."
