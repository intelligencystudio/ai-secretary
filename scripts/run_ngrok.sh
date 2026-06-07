#!/usr/bin/env sh
set -eu

PORT="${PORT:-8787}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is not installed or not in PATH."
  echo "Install it, authenticate it, then run: PORT=$PORT scripts/run_ngrok.sh"
  exit 1
fi

ngrok http "$PORT"
