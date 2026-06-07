#!/usr/bin/env sh
set -eu

PORT="${PORT:-8787}"
HOST="${HOST:-127.0.0.1}"

python3 server.py --host "$HOST" --port "$PORT"
