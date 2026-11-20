# LiquidityGuard

LiquidityGuard is a read-only academic tool for capturing SSI FastConnect Market Data and measuring liquidity from the visible three-level order book. SSI is the only data provider. The project never initializes a Trading client and never sends orders.

## Current capability

- SSI REST: authentication, securities info/summary and master data through the official `ssi-sdk`.
- SSI WebSocket: subscribes only to quote and market-flag topics; a collector stores append-only raw JSONL envelopes.
- Resilience: provider rate-limit awareness, bounded retries, safe error reporting, SDK reconnect, and UI-readable collector health status.
- Public dashboard modes are `LIVE` and `REPLAY`; synthetic fixtures remain development/test-only.

## Set up and verify

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
pytest -q
```

Put credentials only in `.env`; do not commit this file. Follow [the SSI runbook](docs/ssi_api_runbook.md) before enabling a real collection session.

The quote collector no longer falls back to only `FPT,VPB`. With
`SSI_SYMBOLS=` blank, `SSI_COLLECTION_SCOPE=VN30` subscribes the 30 HOSE
constituents published for the July 2026 review. `WATCHLIST` accepts an
explicit comma-separated list; `ALL` resolves every SSI-classified Stock from
the saved `securitiesByBoard` catalogue. Full-market streaming can exceed the
provider's permission or capacity, so VN30 is the bounded default.

Current W2 implementation/evidence is tracked in [the SSI W2 delivery report](docs/w2_ssi_delivery.md). W2 is not accepted until a real VPB/FPT quote is persisted and read back; REST success or a confirmed subscription alone is insufficient.

## Process and replay captures

After the collector writes an authorised raw capture, create or update the local replay database:

```bash
PYTHONPATH=src python -m data.pipeline data/raw/ws/YYYY-MM-DD.jsonl
```

The same command runs safely against `data_sample/synthetic_ssi_quote_envelope.jsonl`. It records canonical quotes in `data/processed/quotes.sqlite`; the replay service relabels returned records as `REPLAY` while preserving `original_source_mode`.

Build the W4-facing mart and W3 QA reports after processing:

```bash
PYTHONPATH=src python -m data.mart
PYTHONPATH=src python -m data.quality_report
PYTHONPATH=src python -m data.coverage_report
PYTHONPATH=src python -m data.replay

# OHLCV daily 5 năm cho watchlist SSI_SYMBOLS
PYTHONPATH=src python -m ssi_api.ohlc_collect --timeframe 1d --years 5

# OHLCV 1 phút cho phân tích nội ngày
PYTHONPATH=src python -m ssi_api.ohlc_collect --timeframe 1m
```

`coverage_report.csv` compares each capture with the declared HOSE session
windows and reports missing edges/downtime. `live_replay_report.json` groups
all stored LIVE captures by date without relabelling them as new LIVE data. See
[the W3 SSI delivery report](docs/w3_ssi_delivery.md) for mapping,
dedup/partial-update policy and the remaining LIVE acceptance gate. OHLC
history is not accepted as a substitute for three-level quote history.

## Dashboard W5

The upgraded Streamlit workspace follows `docs/ui_reference/MASTER_SPEC_LIQUIDITYGUARD.md`
and the pastel/plum reference. Run it from the repository root:

```bash
source "$HOME/.venv/bin/activate"
python -m pip install -e '.[app,dev]'
streamlit run app.py --server.port 8503
```

For Streamlit Community Cloud, select this repository, branch `main`, and set
the main file path to `app.py`. Configure SSI credentials only through
Streamlit Secrets or the deployment environment; never commit `.env`.

Open the full market table at **http://localhost:8503/?view=market**. It lists
1,517 SSI-classified stocks (410 HOSE, 299 HNX, 808 UPCoM), with company/ICB
industry and real daily REST trading data where available. The current capture
has 1,192 stocks with summaries; 325 returned no rows for 11–18/11/2026 and can
be hidden with the availability toggle. Refresh with:

```bash
PYTHONPATH=src python -m ssi_api.market_catalog_collect
```

Open http://localhost:8503 for the restored multi-page dashboard, or
**http://localhost:8503/?view=simulator** for Execution Lab. The default mode is
**REPLAY** and the public UI exposes only LIVE/REPLAY. Change the symbol through
the search/filter bar or Watchlist. The seven pages are Dashboard,
Market Pulse, Simulator, Replay, Charts, Alerts and Settings. They share symbol,
mode, date/snapshot, BUY/SELL and quantity. The Replay page selects only dates
actually stored, with Play/Pause/speed and A/B comparison. Simulator exports
JSON/CSV with provider, mode, symbol, snapshot, quote time, side, Q, filled,
unfilled, VWAP, coverage, impact and validation evidence. The page follows
`docs/ui_reference/REFERENCE_EXECUTION_LAB_MASCOT.png`; its sidebar, topbar,
hero, controls, result/insight strips, 3+2 charts and right rail are scoped to
Simulator so the other six restored pages keep their prior layout.

The UI reads canonical SSI quotes and collector status independently of the
collector. LIVE is refreshed every five seconds and stays blocked when offline,
stale, incomplete or lacking SSI unit/phase evidence. The original SSI/data/
finance modules remain in place. OHLC history is accessible in Market Pulse.
See [the universe catalog](docs/universe_catalog.md) for sector provenance.

```bash
python -m pytest -q
# Optional real-browser acceptance and screenshots; keep Streamlit running.
python -m pip install -e '.[ui-test]'
python -m playwright install chromium
python tests/ui_browser_check.py
```

Screenshots are in [outputs/ui](outputs/ui/). The implementation inventory,
interaction matrix, verification results and remaining data limitations are in
[the UI delivery report](docs/ui_implementation_report.md).

W6 QA coverage and the distinction between synthetic integration tests and
real SSI acceptance are documented in [docs/w6_qa_delivery.md](docs/w6_qa_delivery.md).

The consolidated ten-section W7 report is available at
[docs/w7_final_report.md](docs/w7_final_report.md).

## Project map

- `src/ssi_api`: SSI FastConnect V3 read-only adapter and live-access check.
- `src/data`: raw writer, canonical pipeline, mart, replay, coverage and quality reports.
- `data/raw`: local append-only REST/WS capture files (ignored by Git).
- `docs`: API verification evidence, contract and operating runbook.
