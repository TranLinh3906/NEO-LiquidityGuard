# SSI FastConnect Access Check

**Provider:** SSI FastConnect V3  
**Mode:** Market Data only  
**Current status:** `LIVE_QUOTE_CAPTURED_UNITS_VERIFIED_PHASE_PARTIAL`

## Configuration

- REST URL: CONFIGURED
- Streaming URL: CONFIGURED
- Client ID: PRESENT_IN_LOCAL_ENV
- API key: PRESENT_IN_LOCAL_ENV
- API secret: PRESENT_IN_LOCAL_ENV
- Capture scope: 230 symbols; 201 symbols emitted quotes
- Trading/OTP/private key: intentionally absent

## Evidence

- Unit/integration tests: PASS (`71 passed`)
- Live report: `outputs/qa/ssi_live_access_check.json`
- Authentication/token refresh capability: PASS; no token or payload was logged
- LIVE REST raw: PASS for VPB/FPT info + summary and master data
- WebSocket TLS/heartbeat/subscription list: PASS
- Confirmed subscriptions: quote channels and `market.flag`
- LIVE canonical quote evidence: PASS; 320.102 records are readable
- Strict acceptance: PASS (`REAL_SSI_QUOTE_PERSISTED_AND_READ_BACK`)

## Latest aggregate evidence

- Observed LIVE dates: 16, 18 and 19/11/2026.
- Unit evidence: VND/share and shares, multiplier `1/1`, confirmed by SSI support.
- `price_unit` unknown: 0; `quantity_unit` unknown: 0.
- Phase verified and simulatable: 35.460 snapshots.
- Phase unknown and observation-only: 284.642 snapshots.
- Replay: three LIVE dates, preserving `original_source_mode=LIVE`.
- Remaining coverage target: two future LIVE dates to reach five.

The W4 gate is open per snapshot, not globally: only verified-unit `LO`
snapshots joined to a same-board SSI flag can be simulated. Unknown-phase
history is never promoted using the wall clock.
