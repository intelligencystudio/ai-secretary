#!/usr/bin/env sh
set -eu

PORT="${PORT:-8788}"
HOST="${HOST:-127.0.0.1}"

python3 hr_agent.py --host "$HOST" --port "$PORT"
