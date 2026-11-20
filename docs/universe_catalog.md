# SSI market catalogue — 18/11/2026

The catalogue merges the latest non-empty SSI `masterdata` with
`securitiesByBoard` metadata for HOSE/HNX/UPCoM. Exchange membership alone is
not an equity classification: SSI also returns covered warrants, ETFs, bonds,
funds and instruments with unknown type.

Current capture contains **2,179 unique instruments**, of which SSI explicitly
classifies **1,517 as Stock**: HOSE 410, HNX 299, UPCoM 808. The previous
2,077/2,106 figures counted instruments from masterdata, not just stocks. The
UI now defaults to the Stock filter, with an option to show all instrument
types. Unrecognised types are retained as UNKNOWN.

SSI securities metadata supplies company name and `icb_code`/`icb_name`.
All 1,517 current Stock entries have an ICB industry. Examples: HPG — Thép và
sản phẩm thép; VNM — Thực phẩm; MBB — Ngân hàng; VIC — Bất động sản. Explicit
reviewed overrides are retained for the three existing labels; all other
available sectors have `sector_source=SSI_ICB`. Missing metadata remains
UNCLASSIFIED, never guessed from a ticker.

## Actual daily trading data

`python -m ssi_api.market_catalog_collect` refreshes metadata and queries SSI
daily securities summaries for every Stock instrument, using the SDK's shared
thread-safe rate limiter. It does not enable whole-market quote streaming.
The 11–18/11/2026 capture returned:

* 1,517 requested equities;
* 1,192 equities with summaries, 5,240 dated rows;
* 325 empty responses in this date range; zero failed symbol requests.

Raw REST responses remain in `data/raw/rest/`; daily canonical rows live in
`data/processed/market_catalog.sqlite`. Upserts are keyed by symbol/date and
retain the raw event ID. Missing values remain null; a genuine reported zero
remains zero. Daily REST prices do not imply verified quote-L3 units.

The Market Pulse table shows all stocks by default, includes company, industry,
last daily price, price change, matched volume/value, reference price/date and
availability of L3/daily/1m history. Users can hide rows with no returned daily
summary, search, filter board/type/industry, click a row to select its ticker,
or export the filtered table. The Watchlist is a separate set of favourites,
now defaulting to ten symbols with paging.

Open the table directly: http://localhost:8503/?view=market

```bash
source "$HOME/.venv/bin/activate"
PYTHONPATH=src python -m ssi_api.market_catalog_collect
```

Evidence: `outputs/qa/market_catalog_collect.json`, `outputs/ui/all_market.png`,
`outputs/ui/market_available.png`. Simulation fixtures remain explicitly
SYNTHETIC_TEST. LIVE and Replay financial metrics still require verified L3
units, phase and snapshot completeness.

API references: [SSI securities metadata](https://developers.ssi.com.vn/en/docs/api-reference/data-securitiesByBoard),
[SSI daily summaries](https://developers.ssi.com.vn/en/docs/api-reference/data-securitiesSummary).
