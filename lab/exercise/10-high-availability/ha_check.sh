#!/usr/bin/env bash
# Exercise 10: write + read a memory every second at QUORUM. Ctrl+C to stop.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"
cd "$HERE"
PYTHONPATH="$LAB_DIR" exec uv run --project "$LAB_DIR" --quiet python -u ha_check.py 2> "$LAB_DIR/.data/ha_check.log"
