#!/usr/bin/env bash
# Open cqlsh on scylla-1, in the lab's keyspace when it exists.
# Usage: ./cqlsh.sh                  interactive shell
#        ./cqlsh.sh -e "SELECT ..."  run one statement
set -euo pipefail
NODE="${NODE:-scylla-1}"
if docker exec "$NODE" cqlsh -e "DESCRIBE KEYSPACE plushie_shop" > /dev/null 2>&1; then
  set -- -k plushie_shop "$@"
fi
if [ -t 0 ]; then
  exec docker exec -it "$NODE" cqlsh "$@"
else
  exec docker exec -i "$NODE" cqlsh "$@"
fi
