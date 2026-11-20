# QA output status

`data_quality.json` and `coverage_report.csv` include 320.102 SSI LIVE quotes
from 201 observed symbols across three dates. Units are verified for all
canonical quotes using SSI support evidence; 35.460 snapshots have a same-board
phase and pass the W4 gate. The remaining 284.642 phase-unknown snapshots stay
observation-only.

Coverage remains `OBSERVED_ONLY`: 205 symbol/session rows expose 3.113 missing
edge or downtime gaps and there are zero full symbol sessions.
`live_replay_report.json` proves replay across 16, 18 and 19/11/2026; two future
trading-day captures are still required to reach five observed dates. The
machine-readable seven-issue status is `w2_w4_acceptance_status.json`.
