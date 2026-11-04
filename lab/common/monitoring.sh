#!/usr/bin/env bash
# ScyllaDB Monitoring (Prometheus + Grafana) for the lab cluster. Grafana on port 3000 (the Monitoring tab).
# Usage: monitoring.sh install   clone scylla-monitoring and pull its images (setup.sh)
#        monitoring.sh start     (re)start the stack; the cluster must be up (exercise 01)
#        monitoring.sh stop      stop the stack (reset.sh --all)
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITORING_VERSION=4.16.3
SCYLLA_VERSION=2026.3      # dashboard set, matches scylladb/scylla:2026.3.x
NETWORK=mem0-lab_lab       # the network docker-compose.yml creates, so Prometheus reaches scylla-N by name
DIR="$LAB_DIR/.data/scylla-monitoring"

install() {
  if [ ! -d "$DIR" ]; then
    git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$MONITORING_VERSION" https://github.com/scylladb/scylla-monitoring.git "$DIR"
  fi
  # shellcheck source=/dev/null
  . "$DIR/versions.sh"
  docker pull --quiet "prom/prometheus:$PROMETHEUS_VERSION"
  docker pull --quiet "grafana/grafana:$GRAFANA_VERSION"
}

start() {
  [ -d "$DIR" ] || install
  cat > "$DIR/prometheus/scylla_servers.yml" << EOF
- targets:
    - scylla-1
    - scylla-2
    - scylla-3
  labels:
    cluster: mem0-lab
    dc: datacenter1
EOF
  cd "$DIR"
  ./kill-all.sh > /dev/null 2>&1 || true
  # Grafana 13 downloads its core plugins into grafana/plugins at startup and swaps them in while running,
  # which breaks the Prometheus datasource ("Could not load plugin"). Use the bundled ones instead.
  git clean -fdq grafana/plugins
  # --scrap 5: scrape every 5s instead of 20s, so a stopped node shows up quickly.
  ./start-all.sh -v "$SCYLLA_VERSION" -s prometheus/scylla_servers.yml \
    --no-loki --no-alertmanager --no-renderer --allow-embedding --scrap 5 \
    -c GF_PLUGINS_PREINSTALL_DISABLED=true -D "--network $NETWORK"
  echo "Monitoring is running on port 3000. Open the Monitoring tab."
}

stop() {
  [ -d "$DIR" ] || return 0
  cd "$DIR"
  ./kill-all.sh
}

case "${1:-}" in
  install|start|stop) "$1" ;;
  *) echo "Usage: $0 install|start|stop" >&2; exit 1 ;;
esac
