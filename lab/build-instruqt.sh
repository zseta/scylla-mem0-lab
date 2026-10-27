#!/usr/bin/env bash
# Builds the Instruqt challenge's assignment.md from intro.md + every exercise/*/lab.md.
# Edit the lab.md files, then run this script. Do not edit assignment.md by hand.
set -euo pipefail
LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
CHALLENGE="$LAB_DIR/../instruqt/01-workshop"
OUT="$CHALLENGE/assignment.md"

# Every heading moves one level down (# -> ##), except inside code blocks.
demote() {
  awk '/^```/ { fence = !fence } !fence && /^#/ { print "#" $0; next } { print }' "$1"
}

# frontmatter.yml holds the ids Instruqt assigned on the first push. Keep them.
{
  cat "$CHALLENGE/frontmatter.yml"
  echo
  cat "$LAB_DIR/intro.md"
  for f in "$LAB_DIR"/exercise/*/lab.md; do
    echo
    echo "---"
    echo
    demote "$f"
  done
} > "$OUT"

echo "Wrote $OUT ($(wc -l < "$OUT") lines)"
