#!/usr/bin/env bash
# Pre-start script: installs and downloads everything before attendees arrive,
# so no exercise waits on a download. Safe to run more than once.
# Runs as root on the lab VM (Ubuntu). Takes 5-10 minutes on a fresh VM.
set -euxo pipefail

LAB_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="/root/.local/bin:$HOME/.local/bin:$PATH"

# 1. Kernel setting for running several ScyllaDB nodes on one host
sysctl -w fs.aio-max-nr=1048576
echo "fs.aio-max-nr = 1048576" > /etc/sysctl.d/99-scylladb.conf

# 2. Docker
if ! command -v docker > /dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# 3. uv and Python 3.14
if ! command -v uv > /dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
grep -qs '.local/bin' /root/.bashrc || echo 'export PATH="/root/.local/bin:$PATH"' >> /root/.bashrc
uv python install 3.14

# 4. Python dependencies: mem0 + ScyllaDB provider, Gemini SDK, sentence-transformers (CPU torch), Streamlit
uv sync --project "$LAB_DIR" --frozen

# 5. Embedding model, downloaded once into the Hugging Face cache
uv run --project "$LAB_DIR" python -c \
  "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# 6. Docker images for exercise 01
docker compose -f "$LAB_DIR/exercise/01-start-scylladb/docker-compose.yml" pull

mkdir -p "$LAB_DIR/.data"
chmod +x "$LAB_DIR"/*.sh "$LAB_DIR"/common/*.sh "$LAB_DIR"/exercise/*/*.sh
echo "Lab setup complete."
