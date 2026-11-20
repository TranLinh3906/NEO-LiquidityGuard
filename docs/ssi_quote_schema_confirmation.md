# SSI Quote schema confirmation

**Evidence reference:** `SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19`  
**Recorded:** 19/11/2026  
**Source:** Direct SSI customer-support response supplied by the project owner.

SSI confirmed the following semantics for the current Quote version:

1. Quote prices are denominated in VND. The normalization multiplier to
   VND/share is therefore `1`.
2. Quote quantities are numbers of shares. The normalization multiplier to
   shares is therefore `1`.
3. A Quote contains the latest complete bid/ask levels. An empty level is
   represented by `["0", "0"]`.

Implementation policy:

- Preserve raw price and quantity fields unchanged.
- Normalize with price multiplier `1` and quantity multiplier `1`.
- Treat zero/zero as an explicitly empty level, never as executable liquidity.
- `complete_book_verified=true` verifies snapshot semantics; it does not make
  an empty level executable and does not bypass structural validation.
- LIVE simulation still requires a same-board SSI `market.flag`, an allowed
  phase, a non-stale online collector and the three executable levels required
  by the LiquidityGuard three-level model.
- Historical raw events may be re-normalized with `--replace-existing`; their
  `raw_event_id`, `quote_id` and immutable raw envelopes remain unchanged.
