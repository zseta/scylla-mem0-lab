#!/usr/bin/env bash
# Exercise 00: check the LLM, then start the bot (no memory, no database).
# On Instruqt the bot uses Claude on Amazon Bedrock: the track setup writes LLM_PROVIDER=bedrock to lab/.env.
# If Bedrock does not answer, or when running locally, it asks for your Gemini API key once and saves it to lab/.env.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$HERE/../.." && pwd)"
ENV_FILE="$LAB_DIR/.env"
mkdir -p "$LAB_DIR/.data"

if grep -qs '^LLM_PROVIDER=bedrock' "$ENV_FILE"; then
  if PYTHONPATH="$LAB_DIR" uv run --project "$LAB_DIR" --quiet python -m common.check_llm 2> "$LAB_DIR/.data/check_llm.log"; then
    "$LAB_DIR/common/run_app.sh" "$HERE"
    exit 0
  fi
  echo "Amazon Bedrock is not answering (details in $LAB_DIR/.data/check_llm.log). Switching to Gemini."
  sed -i '/^LLM_PROVIDER=/d' "$ENV_FILE"
fi

if ! grep -qs '^GOOGLE_API_KEY=.\+' "$ENV_FILE" "$LAB_DIR/../.env" && [ -z "${GOOGLE_API_KEY:-}" ]; then
  read -rsp "Paste your Gemini API key (from https://aistudio.google.com/apikey): " key
  echo
  echo "GOOGLE_API_KEY=$key" >> "$ENV_FILE"
  echo "Saved to $ENV_FILE"
fi

"$LAB_DIR/common/run_app.sh" "$HERE"
