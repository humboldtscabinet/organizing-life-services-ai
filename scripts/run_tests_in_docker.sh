#!/bin/sh
set -eu

docker run --rm \
  -e OLS_API_KEY=REDACTED-API-KEY \
  -v "$(pwd):/workspace" \
  -w /workspace \
  python:3.11-slim \
  sh -lc '
    apt-get update >/dev/null &&
    apt-get install -y --no-install-recommends gcc git libpq-dev >/dev/null &&
    python -m pip install --upgrade pip >/dev/null &&
    pip install -r requirements.txt pytest >/dev/null &&
    pytest -q
  '
