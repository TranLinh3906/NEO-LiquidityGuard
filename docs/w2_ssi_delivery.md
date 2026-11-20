# W2 — SSI FastConnect Connection Layer Delivery

**Run date:** 19/11/2026, Asia/Ho_Chi_Minh  
**Scope:** SSI Market Data only; 230 subscribed symbols; no Trading/FCO/order API.  
**Overall status:** `LIVE_QUOTE_ACCEPTED / UNITS_VERIFIED / PHASE_PER_SNAPSHOT / W4_GATE_OPEN`

## Work-item status

| ID | Result | Implementation and evidence |
|---|---|---|
| W2.01 | PASS | `ssi-sdk>=3.3.2,<4`, `certifi`, `.env.example`, and `src/ssi_api` are present. |
| W2.02 | PASS | Production REST and WSS were reached. Market Data auth passed; server subscription list contained `quote.VPB`, `quote.FPT`, `market.flag`. |
| W2.03 | PASS | Initial `authenticate()` uses API Key/Secret without OTP. Token metadata confirms refresh support; secrets/tokens are never reported or persisted. |
| W2.04 | PASS | Official SDK REST transport provides timeout, GET-only retry, exponential backoff, client rate cap and response-header rate adaptation. Configuration is environment-driven. |
| W2.05 | PASS_LIVE_REST | Real securities info for VPB/FPT and master data were saved; latest run returned 2,120 master-data items. Summaries can be empty outside the provider update window. |
| W2.06 | PASS_RAW / UNIT_VERIFIED | REST/WS raw events are persisted with SSI metadata. SSI support confirmed VND prices, share quantities and latest complete book semantics on 19/11/2026; multipliers are `1/1`. |
| W2.07 | PASS_QUOTE / PHASE_PARTIAL | Secure WebSocket produced 320.102 canonical LIVE quotes over three dates. Market flag is subscribed before quote on connect/reconnect; 35.460 snapshots have verified phase. |
| W2.08 | PASS_LIVE_READBACK | 320.102 canonical LIVE quotes from 201 observed symbols are persisted and readable. |
| W2.09 | PASS | SDK auto-reconnect, token cycling, re-subscribe, heartbeat and bounded backoff are enabled; reconnect clears the phase joiner until a new flag arrives. |
| W2.10 | PASS | Runtime status records online/offline, message count, last message, heartbeat count/time, subscriptions and reconnect count. |
| W2.11 | PASS | Allow-list permits only auth/refresh, Market Data REST, quote and market-flag. Trading, FCO, account, portfolio and orders are absent/blocked. |
| W2.12 | PASS | `docs/ssi_api_runbook.md` documents credentials, collector execution, strict acceptance and troubleshooting. |

## Live evidence observed

- Authentication: `PASS`; refresh token capability available in memory.
- REST VPB: securities info `PASS`, securities summary `PASS`.
- REST FPT: securities info `PASS`, securities summary `PASS`.
- Master data: `PASS`, 2,120 records.
- WebSocket TLS: `PASS` using verified `certifi` CA bundle; verification was not disabled.
- Subscription list: `quote.VPB`, `quote.FPT`, `market.flag`.
- Heartbeat: observed.
- Canonical LIVE quotes: `320.102` from 201 observed symbols across three dates.
- Simulatable LIVE snapshots: `35.460`; phase-unknown observation-only snapshots: `284.642`.
- Unit policy: `VND_PER_SHARE` and `SHARES`, multipliers `1/1`; evidence reference `SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19`.
- Market flags on the 18/11/2026 13:25 ICT run: `0`; quote phase is therefore `UNKNOWN` and LIVE simulation remains blocked.
- Raw envelopes now include `market_phase_source`, `market_phase_board` and `market_phase_received_at`; the joiner uses only same-board flags at or before the quote provider timestamp and resets on reconnect.

Machine-readable evidence: `outputs/qa/ssi_live_access_check.json`.

The current aggregate evidence verifies authentication, TLS, heartbeat,
quote/market-flag subscriptions and readback. The strict transport gate is
`PASS`; W4 is open only for the 35.460 snapshots with both verified units and
a same-board SSI market phase.

## Strict W2 acceptance gate

W2 is accepted only when all are true in one run:

1. At least one real SSI `QuoteMessage` for VPB or FPT is received.
2. Its raw envelope is appended under `data/raw/ws/` with `mode=LIVE`.
3. The same `raw_event_id` is read back from disk.
4. The persisted envelope parses into at least one canonical quote.
5. `outputs/qa/ssi_live_access_check.json` contains `acceptance.status=PASS`.

Authentication, REST success, subscription acknowledgement or a connected socket alone do not pass this gate. Current result is `PASS/REAL_SSI_QUOTE_PERSISTED_AND_READ_BACK`; W4 still checks market phase per snapshot.

The three data-fix gates are separate from transport acceptance: price and
quantity become verified only with explicit multipliers plus an evidence
reference; a quote is phase-joined only from a received SSI `market.flag` for
the same board and an earlier/equal provider time; absent flags and reconnect
gaps remain `UNKNOWN` and are not promoted to LIVE-eligible data.
