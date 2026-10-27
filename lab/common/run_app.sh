#!/usr/bin/env bash
# Starts an exercise's Streamlit app on port 8501 (the App tab).
# Stops the app of the previous exercise first, so the App tab always shows the current one.
# Usage: run_app.sh <exercise-dir>
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXERCISE_DIR="$(cd "$1" && pwd)"
PORT=8501
LOG="$LAB_DIR/.data/app.log"
mkdir -p "$LAB_DIR/.data"

pkill -f "streamlit run app.py --server.port $PORT" 2>/dev/null || true
sleep 1

# ScyllaDB Design System (light theme) colors for Streamlit's built-in widgets
export STREAMLIT_THEME_BASE=light
export STREAMLIT_THEME_PRIMARY_COLOR="#0079b3"
export STREAMLIT_THEME_BACKGROUND_COLOR="#ffffff"
export STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR="#f5f9fd"
export STREAMLIT_THEME_TEXT_COLOR="#161a34"
export PYTHONPATH="$LAB_DIR"

cd "$EXERCISE_DIR"
nohup uv run --project "$LAB_DIR" --quiet streamlit run app.py --server.port "$PORT" \
  --server.address 0.0.0.0 --server.headless true \
  --server.enableCORS false --server.enableXsrfProtection false \
  --browser.gatherUsageStats false --client.toolbarMode minimal > "$LOG" 2>&1 &

for _ in $(seq 1 60); do
  if curl -fs "http://localhost:$PORT/_stcore/health" > /dev/null 2>&1; then
    echo "App is running on port $PORT. Open the App tab (reload it if it was already open)."
    exit 0
  fi
  sleep 1
done
echo "The app did not start. Last lines of $LOG:" >&2
tail -20 "$LOG" >&2
exit 1
