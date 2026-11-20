# LiquidityGuard — UI delivery, updated 19/11/2026

> Current UI decision: the prior seven-page dashboard and mascot layout were
> restored from `outputs/ui/pre_live_replay_ui_20261119.tgz`. The only public
> mode change retained is removal of `SYNTHETIC_TEST`; users can select only
> LIVE or REPLAY. Synthetic fixtures and W4 unit tests remain in development.

## Locked Execution Lab update

The Simulator route now follows `REFERENCE_EXECUTION_LAB_MASCOT.png` and
`EXECUTION_LAB_UI_LOCKED_SPEC.md` as its only visual source. At the acceptance
viewport 1672×941 the measured shell is: sidebar 228px, topbar x=244/height
63px, center 997px, right rail 415px and hero 174px. The center order is Hero →
controls → results → insight → three charts → two charts → formulas. The right
rail contains Watchlist → Session Snapshot → Data Trust. This layout is scoped
to Simulator and does not redesign the remaining six pages.

Every result is derived from the selected SSI/synthetic quote through the
existing finance modules. A simulation click stores symbol, mode, snapshot ID,
side and quantity together; LIVE refresh therefore cannot combine levels from
different snapshots. Only L1–L3 are swept. Unfilled quantity is not labelled or
priced as L4. Synthetic fixtures are deterministic and available for every
valid symbol in the captured universe, while remaining conspicuously labelled
`SYNTHETIC_TEST` and never being written to SSI storage.

## Scope and preservation

Implementation follows the three user-supplied references in `docs/ui_reference/`.
The entrypoint remains `src/app/dashboard.py`; Streamlit now renders native
controls with reusable Python view models, CSS cards and Plotly charts. The
prior UI is preserved at `outputs/ui/dashboard_before.py`, with a before-image
at `outputs/ui/before_desktop.png`. This workspace has no Git repository, so no
feature branch was created. No SSI credentials, trading operations, quote raw
files, finance formulas or historical evidence labels were changed by this UI
task. `src/app/universe.py` only skips non-masterdata lines before JSON parsing.

## Files created or updated

| File | Purpose |
|---|---|
| `src/app/dashboard.py` | Entrypoint, shared workspace, atomic snapshot selection, replay timer and 5-second LIVE polling |
| `src/app/state.py` | Shared state and navigation/mode/symbol transitions |
| `src/app/view_models.py` | Read-only SQLite access, explicit synthetic fixtures, SSI evidence/freshness gates, backend metrics/simulation |
| `src/app/styles.py` | Supplied HEX tokens, plum shell, pastel cards, responsive layout, reduced-motion support |
| `src/app/components.py` | Header/rail, search/filter, six KPIs, mascot hero, progress, simulation strip, utilities and formula popovers |
| `src/app/pages.py` | All seven functional pages, replay/compare, exports, Data Trust, preferences |
| `src/app/charts.py` | Five primary and four advanced Plotly views with shared styling |
| `src/app/assets/mascot.png` | Separate generated transparent mascot asset |
| `src/app/universe.py` | Avoid parsing large unrelated OHLC envelopes when reading the symbol catalogue |
| `.streamlit/config.toml` | Reproducible light/plum native-widget theme |
| `pyproject.toml` | Plotly app dependency, optional Playwright acceptance dependency, mascot package data |
| `tests/test_ui_workspace.py` | Data gates, snapshot consistency, 87.5% coverage, monotonic coverage, seven-page state tests |
| `tests/ui_browser_check.py` | Repeatable browser interactions and desktop/mobile captures |
| `tests/execution_lab_browser_check.py` | Locked-layout interactions: SELL, quantity, CTA, HPG, LIVE block |
| `tests/screenshot_execution_lab.py` | 1672×941 screenshot, geometry and horizontal-overflow evidence |
| `README.md`, this report | Run instructions, delivery and limitations |

## Functional interaction matrix

| Action | Result |
|---|---|
| Header or left navigation | Opens Dashboard, Market Pulse, Simulator, Replay, Charts, Alerts, Settings while retaining shared inputs |
| Mobile navigation | Native compact selector replaces desktop menu and rail below 760px |
| Search, exchange, sector | Filters actual SSI universe; symbol updates the workspace; unknown sectors remain explicit |
| Click Watchlist | Selects ticker and clears incompatible snapshot/result; no invented LIVE price/change/sparkline |
| BUY/SELL and quantity | Recomputes using existing `finance.execution.simulate_sweep`; positive integer enforced |
| Mô phỏng | Captures the atomic snapshot; disabled on failed validation; exports include metadata and mode |
| Quick Tasks | Opens Simulator, recorded-date Replay, or A/B Charts comparison |
| Replay | Chooses a stored date, snapshot slider, reset, continuous Play/Pause and 1/2/5/10 snapshots per second |
| Replay → Simulator | Preserves the selected historical snapshot and REPLAY label |
| Compare | Compares two stored snapshots with times, trust labels, metrics and paired depth charts when eligible |
| Chart ⓘ | Opens formula/units/limits popover; blocked charts show an explanation |
| Alerts | Shows exact validation reasons, quote age, source/phase/units and snapshot lineage; links related views |
| Settings | Applies density, number formatting and LIVE stale threshold; download/upload safe preferences JSON |

The Dashboard has Spread, Bid Depth, Ask Depth, OBI, Coverage and Data Trust.
Execution Progress equals passed steps / 4; it is not copied from the concept.
Chart Studio contains Depth Mirror, Cumulative Depth, Bid/Ask Balance, Sweep
Allocation, Coverage Curve, VWAP Impact, Spread, OBI and Depth timelines.
Coverage decreases or stays constant as requested volume increases on a fixed
book. Sweep segments are L1–L3 plus Unfilled, never L4+. Timeline traces contain
null separators for gaps over 60 seconds. Session Snapshot is labelled as an
observed window; historical age is shown without treating replay as realtime.

## Validation and screenshots

`python -m pytest -q`: **73 passed**.
New tests include UI/back-end eligibility, stale online quote rejection,
350/400 = **87.5%**, no mutation of the input snapshot, non-increasing coverage,
all seven routes retaining shared state, and blocked LIVE simulation.

Chromium acceptance opens the real Streamlit application at localhost:8503,
clicks Watchlist, changes BUY/SELL and quantity, visits all seven pages, verifies
LIVE gating and checks responsive layout without horizontal overflow. Separate
real-browser verification uses **57 actual FPT SSI snapshots from 18/11/2026**
to verify continuous Replay advances IDs and Pause keeps its ID unchanged. This
verifies playback/metadata, not financial eligibility of those historical rows.

| Artifact | Content |
|---|---|
| `outputs/ui/dashboard_desktop.png` | Final Dashboard, 1448×1086, labelled synthetic |
| `outputs/ui/dashboard_full.png` | Expanded 1448×1210 view showing the complete chart grid |
| `outputs/ui/dashboard_1366.png` | 1366×768 viewport |
| `outputs/ui/dashboard_mobile.png` | 390×844 viewport, compact navigation and two-column KPIs |
| `outputs/ui/dashboard_tablet.png` | 1000×900 viewport; right utilities stack below content without horizontal overflow |
| `outputs/ui/market_pulse.png` | Market Pulse page |
| `outputs/ui/simulator.png` | Simulation/partial coverage page |
| `outputs/ui/replay.png` | Replay fixture page |
| `outputs/ui/replay_live.png` | Actual SSI replay, with original date and blocked financial trust |
| `outputs/ui/charts.png` | Chart Studio |
| `outputs/ui/alerts.png` | Alerts and source-quality table |
| `outputs/ui/settings.png` | Settings/preferences |
| `outputs/ui/live_blocked.png` | Genuine SSI rows remain blocked; metrics/charts suppressed |
| `outputs/ui/browser_checks.json` | Browser acceptance outcomes |
| `outputs/ui/execution_lab_after_1672x941.png` | Final locked Execution Lab render at the acceptance viewport |
| `outputs/ui/execution_lab_geometry.json` | Measured geometry, chart count, browser errors and overflow check |
| `outputs/ui/execution_lab_browser_checks.json` | Browser interaction outcomes for the locked page |

Compared visually with `reference_dashboard.png`: plum shell, top/left nav,
six pastel KPI cards, central mascot hero/progress, simulator strip, 3+2 chart
grid and four right-side utilities are implemented. Data Health replaces the
concept's palette panel; palette tokens are in Settings. Additional shared
filters and a conspicuous mode label occupy space above KPIs. Native controls
and the separate mascot differ from the concept. The viewport scrolls to show
remaining content on smaller screens; mobile uses stacked sections. Fonts use
Nunito Sans/Inter when available, with system sans-serif fallback. The reference
is never used as an app background.

## Real data limitations

LIVE remains conditional on the selected snapshot's unit evidence, full-book
verification, same-board/effective market.flag, lineage, freshness and current
collector heartbeat. An offline/stale collector blocks LIVE even when stored
REPLAY rows are eligible. Missing symbols remain selectable with an honest
no-data state; OHLCV is never used to synthesize bid/ask depth. The dashboard
does not create additional trading days or fill missing quote history.
Watchlist configuration is session UI state; collector scope/permissions are
configured independently. No real orders are submitted.

## Mascot provenance

Created with the built-in imagegen tool; final workspace asset:
`src/app/assets/mascot.png`. Transparency is preserved. Prompt:

> Use case: stylized-concept. Asset type: isolated transparent PNG mascot for the LiquidityGuard dashboard. Create one adorable premium 3D raccoon liquidity guardian, warm cream-beige fur, cocoa eye mask, blush cheeks, large expressive friendly eyes, lilac aviator goggles on its head, soft lavender protective vest with a small heart-shaped shield. Seated behind a translucent lilac laptop with subtle abstract candlestick decorations, waving one paw. Warm sand pedestal, a couple of small soft lilac cloud puffs. Centered full character and laptop, no clipping, square composition, front three-quarter view, soft studio lighting, Pixar-like rounded toy clay materials and subtle velvet texture. Palette: deep plum #3E2F4F, dusty lavender #BDAFD1, soft lilac #DCCFF0, warm sand #D7B38C, cream #F2E6D7, blush #F3C9DD. No words, numbers, text, logos or watermark. Transparent background with actual alpha. This is a decorative character only, no complete UI.
