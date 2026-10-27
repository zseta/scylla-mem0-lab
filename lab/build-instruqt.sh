#!/usr/bin/env bash
# Builds the Instruqt challenge's assignment.md from intro.md + every exercise/*/lab.md.
# Tab names in bold (**App**) become links that switch to that tab.
# Edit the lab.md files, then run this script. Do not edit assignment.md by hand.
set -euo pipefail
LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
CHALLENGE="$LAB_DIR/../instruqt/01-workshop"
OUT="$CHALLENGE/assignment.md"

# Tab titles in frontmatter.yml order. Instruqt switches tabs with [text](tab-N), N counted from zero.
TABS="$(awk '/^tabs:/ { in_tabs = 1; next } in_tabs && /^[^ -]/ { in_tabs = 0 }
             in_tabs && /^  title:/ { sub(/^  title: */, ""); print }' "$CHALLENGE/frontmatter.yml")"

# Outside code blocks: **App**, **Terminal**, ... become links that switch to that tab.
# With "demote", every heading also moves one level down (# -> ##).
prepare() {
  awk -v tabs="$TABS" -v demote="${2:-}" '
    BEGIN { n = split(tabs, title, "\n") }
    /^```/ { fence = !fence; print; next }
    fence { print; next }
    {
      for (i = 1; i <= n; i++) gsub("\\*\\*" title[i] "\\*\\*", "[**" title[i] "**](tab-" (i - 1) ")")
      if (demote && /^#/) $0 = "#" $0
      print
    }' "$1"
}

# frontmatter.yml holds the ids Instruqt assigned on the first push. Keep them.
{
  cat "$CHALLENGE/frontmatter.yml"
  echo
  prepare "$LAB_DIR/intro.md"
  for f in "$LAB_DIR"/exercise/*/lab.md; do
    echo
    echo "---"
    echo
    prepare "$f" demote
  done
} > "$OUT"

echo "Wrote $OUT ($(wc -l < "$OUT") lines)"
