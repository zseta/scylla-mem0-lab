#!/usr/bin/env bash
# Exercise 09: seed memories for many customers, then benchmark search latency.
# Usage: ./load.sh [customers] [threads] [seconds]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"
CUSTOMERS="${1:-200}"
THREADS="${2:-8}"
SECONDS_PER_TEST="${3:-10}"

cd "$HERE"
export PYTHONPATH="$LAB_DIR"
uv run --project "$LAB_DIR" --quiet python seed.py "$CUSTOMERS" 5 "$THREADS" 2> "$LAB_DIR/.data/seed.log"
echo
uv run --project "$LAB_DIR" --quiet python bench.py "$THREADS" "$SECONDS_PER_TEST" 2> "$LAB_DIR/.data/bench.log"
