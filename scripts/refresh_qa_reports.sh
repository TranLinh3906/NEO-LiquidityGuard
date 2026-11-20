#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

PYTHONPATH=src .venv/bin/python -m data.quality_report
PYTHONPATH=src .venv/bin/python -m data.coverage_report
PYTHONPATH=src .venv/bin/python -m data.replay
PYTHONPATH=src .venv/bin/python -m data.acceptance_status
