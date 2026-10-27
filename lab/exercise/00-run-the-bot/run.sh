#!/usr/bin/env bash
# Exercise 00: save your Gemini API key, then start the bot (no memory, no database).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"

if ! grep -qs '^GOOGLE_API_KEY=.\+' "$LAB_DIR/.env" && [ -z "${GOOGLE_API_KEY:-}" ]; then
  read -rsp "Paste your Gemini API key (from https://aistudio.google.com/apikey): " key
  echo
  echo "GOOGLE_API_KEY=$key" > "$LAB_DIR/.env"
  echo "Saved to $LAB_DIR/.env"
fi

"$LAB_DIR/common/run_app.sh" "$HERE"
