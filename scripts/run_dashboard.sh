#!/bin/sh
set -eu
project_root="/Users/thylnh.iu/Documents/Neo-LiquidityGuard"
cd "$project_root"
exec env PYTHONPATH=src "$project_root/.venv/bin/streamlit" run src/app/dashboard.py \
  --server.port 8503 --server.headless true
