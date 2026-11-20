# Finance Validation — SYNTHETIC_TEST

| Scenario | Expected | Implementation result | Status |
|---|---:|---:|---|
| Spread (29,800 − 29,750) | 50 | 50 | PASS |
| Bid depth | 230,000 | 230,000 | PASS |
| Ask depth | 280,000 | 280,000 | PASS |
| OBI | -0.098039… | -0.098039… | PASS |
| BUY 100,000 VWAP | 29,820 | 29,820 | PASS |
| BUY 400,000 filled / unfilled | 280,000 / 120,000 | 280,000 / 120,000 | PASS |
| SELL 150,000 VWAP | 29,733.3333… | 29,733.3333… | PASS |

These are fixture-only arithmetic checks, not a LIVE market validation. Execution invariants tested: `0 ≤ filled ≤ requested`, `unfilled = requested - filled`, and filled VWAP is derived only from consumed levels.
