#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"

symbols=$(.venv/bin/python -c 'import json; print(",".join(json.load(open("outputs/qa/ssi_capture_morning_20261119_230symbols.json"))["symbols"]))')
run_date=$(date +%Y%m%d)

set +e
env PYTHONPATH=src .venv/bin/python -m ssi_api.session_capture \
  --env .env \
  --window full \
  --symbols "$symbols" \
  --skip-symbol-rest \
  --report "outputs/qa/ssi_capture_full_${run_date}_230symbols.json"
capture_status=$?
set -e

# Reconcile newly appended immutable raw quotes with the provider-confirmed
# unit policy. Existing rows are updated idempotently by raw-event identity.
env PYTHONPATH=src .venv/bin/python -m data.pipeline data/raw/ws/*.jsonl \
  --price-multiplier 1 --quantity-multiplier 1 \
  --unit-evidence-ref SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19 \
  --complete-book-verified --allowed-phase LO --replace-existing
scripts/refresh_qa_reports.sh
exit "$capture_status"
