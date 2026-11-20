# W2–W4 Execution Report

**Run:** 19/11/2026, Asia/Ho_Chi_Minh  
**Safety scope:** read-only market data; no order/amend/cancel endpoint exists in the allow-list.  
**Active provider:** SSI FastConnect V3 Market Data is the sole provider; the former adapter and operational evidence have been removed.  
**Automated result:** `71 passed`; Python compilation passed; dependency check reported no broken requirements.
**Evidence modes:** SSI authentication, REST, secure WSS, heartbeat, 230 subscriptions and 320.102 canonical LIVE QuoteMessages are verified. SSI support evidence confirms VND/share and shares with multiplier `1/1`; 35.460 snapshots also have a valid same-board phase and pass the W4 gate.

Status meanings:

- `PASS`: implemented and verified locally.
- `PASS_SYNTHETIC`: verified with labelled fixture/replay; LIVE evidence is still required.
- `BLOCKED_LIVE`: LIVE proof is unavailable because credentials, permission, connectivity or an authorised response is still missing.

## W2 — SSI FastConnect REST, WebSocket and collector

| ID | Status | Evidence and result |
|---|---|---|
| W2.01 | PASS | Project imports, editable package metadata, `.env` ignored, safe `.env.example`, test suite and directory layout verified. |
| W2.02 | PASS | SSI production REST and WSS were reached; Market Data auth passed and the server listed `quote.VPB`, `quote.FPT`, `market.flag`. |
| W2.03 | PASS | Initial no-OTP Market Data authentication succeeded; token metadata shows refresh capability without persisting token values. |
| W2.04 | PASS | SDK timeout, GET retry, exponential backoff, dynamic rate-limit observation and a configurable client cap are enabled. |
| W2.05 | PASS_LIVE_REST | Real securities info/summary for VPB/FPT and 2,120 master-data records were retrieved. |
| W2.06 | PASS_LIVE_VERIFIED | `price_unit=VND_PER_SHARE`, `quantity_unit=SHARES`, multiplier `1/1` and complete-book semantics are backed by SSI support evidence; market phase remains per-snapshot. |
| W2.07 | PASS_QUOTE / PHASE_PARTIAL | Verified TLS WSS, heartbeat, quote and market-flag subscriptions; flag is subscribed before quote on initial connect/reconnect. 35.460 stored snapshots have a valid same-board phase; 284.642 historical snapshots remain UNKNOWN. |
| W2.08 | PASS_LIVE_READBACK | 320.102 SSI LIVE canonical quotes across 201 observed symbols are persisted and readable. |
| W2.09 | PASS | SDK auto-reconnect, token cycling, re-subscribe, heartbeat and connection-event status are enabled; reconnect clears phase join state. |
| W2.10 | PASS | Runtime status tracks online/offline, message/heartbeat counts, last timestamps, subscriptions and reconnect count. |
| W2.11 | PASS | The allow-list contains only Market Data authentication/read/stream operations. Trading operations are rejected before SDK/network I/O. |
| W2.12 | PASS | SSI credential setup, REST/stream collection, troubleshooting and evidence labelling are documented in `docs/ssi_api_runbook.md`. |

## W3 — Data engineering and replay

| ID | Status | Evidence and result |
|---|---|---|
| W3.01 | PASS | Immutable raw JSONL + canonical SQLite + runtime-status separation documented. |
| W3.02 | PASS_LIVE | Data dictionary covers type, source, null policy, timezone and verified SSI units. |
| W3.03 | PASS_LIVE | SSI `QuoteMessage` WS envelopes normalize to the L3 contract; REST reference data remains separate and is never misclassified as an order-book snapshot. |
| W3.04 | PASS | Numeric strings, null, ATO/ATC, negative/invalid quantity, level order and crossed book are validated with quality flags. |
| W3.05 | PASS | Deterministic quote IDs and raw-event duplicate policy retain multiple valid same-second updates. |
| W3.06 | PASS | SQLite commits canonical records with symbol, receive time, source, levels and flags; replay queries are consistent. |
| W3.07 | PASS_LIVE_OBSERVED / 2_DAYS_PENDING | Three observed SSI dates and 320.102 quotes; 205 symbol-session rows report opening/closing edges and downtime. Target 5 LIVE dates still needs two future trading days. |
| W3.08 | PASS_LIVE_MULTI_SESSION | Replay covers 16, 18 and 19/11/2026 and preserves `original_source_mode=LIVE`. |
| W3.09 | PASS_LIVE_OBSERVED | Quality report records 3.113 session downtime gaps, provenance, missing phase and book-level omissions without filling history. |
| W3.10 | PASS | Redacted synthetic sample and provenance/limitations documentation are present. |

Idempotency evidence: first pipeline run inserted 1 quote; the second run over the same raw event inserted 0. Replay returned exactly 1 record.

## W4 — Financial analytics and execution simulation

| ID | Status | Evidence and result |
|---|---|---|
| W4.01 | PASS | Formula assumptions specify direction, denominators, zero handling, LO phase, units and no-fee default. |
| W4.02 | PASS | Eligibility rejects stale/partial/unverified-unit/ATO-ATC/invalid/crossed/non-LO books. |
| W4.03 | PASS_SYNTHETIC | Absolute spread, mid, percent and bps match hand calculations; invalid best prices return null. |
| W4.04 | PASS_SYNTHETIC | Bid/ask quantity and notional depth use exactly three levels and require verified unit metadata. |
| W4.05 | PASS_SYNTHETIC | OBI is bounded by [-1,1]; zero total depth returns null and is described as displayed resting volume only. |
| W4.06 | PASS_SYNTHETIC | BUY consumes ASK 1→3; SELL consumes BID 1→3; partial fill never extrapolates level four. |
| W4.07 | PASS_SYNTHETIC | Coverage, filled-only VWAP, notional and side-aware slippage handle partial/no-fill without division by zero. |
| W4.08 | PASS | Hand examples cover KPI, BUY, SELL, one/multiple levels, over-depth, ATO/null/negative quantity and empty book. |
| W4.09 | PASS | Explanation is conditional and explicitly avoids prediction or investment advice. |
| W4.10 | PASS_SYNTHETIC | History sorts by receive time and computes each point from its own snapshot. Real-window coverage remains pending. |
| W4.11 | PASS_SYNTHETIC | Tests assert `0 ≤ filled ≤ requested`, exact unfilled quantity and VWAP within consumed price levels. LIVE raw comparison remains pending. |

Synthetic end-to-end result from the stored sample:

- Spread: 100; spread: 9.995002498750624… bps.
- Bid depth: 2,300; ask depth: 2,700; OBI: -0.08.
- BUY 1,000: filled 1,000; unfilled 0; VWAP 100,130.
- SELL 1,000: filled 1,000; unfilled 0; VWAP 100,000.

## Gate status

| Gate | Status | Meaning |
|---|---|---|
| H01 | OPEN | Repository, environment, imports and tests work. |
| H02 | OPEN_LIVE | Successful SSI REST evidence exists. |
| H03 | OPEN_SYNTHETIC | Canonical fixture exists. |
| H04 | OPEN | Eligibility/liquidity tests pass. |
| H05 | OPEN_LIVE | Real SSI `QuoteMessage` evidence exists. |
| H06 | OPEN_LIVE | SSI QuoteMessage normalization is verified on stored LIVE data. |
| H07 | OPEN_LIVE | Append/status durability and readback work on LIVE data. |
| H08 | OPEN_LIVE | 320.102 canonical SSI quotes exist; 35.460 pass the simulation gate. |
| H09 | OPEN | BUY/SELL/partial/no-fill simulation tests pass. |
| H10 | OPEN_REPLAY | Replay covers three stored LIVE dates. |

## Next LIVE rerun

After creating an SSI Market Data key and filling the three local SSI credential fields:

```bash
PYTHONPATH=src .venv/bin/python -m ssi_api.live_check --listen-seconds 60
PYTHONPATH=src .venv/bin/python -m data.pipeline data/raw/rest/YYYY-MM-DD.jsonl data/raw/ws/YYYY-MM-DD.jsonl
.venv/bin/pytest -q
```

Do not set `SSI_LIVE_CONFIRMED=true` until at least one successful, redacted REST raw event and one genuine SSI `QuoteMessage` raw event exist.
