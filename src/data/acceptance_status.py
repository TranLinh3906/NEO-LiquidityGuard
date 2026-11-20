"""Consolidated W2-W4/W3 live-evidence status without fabricating history."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def build_status(quality: dict[str, Any], replay: dict[str, Any], coverage: list[dict[str, str]]) -> dict[str, Any]:
    total = int(quality.get("quote_count") or 0)
    blocking = quality.get("w4_live_gate", {}).get("blocking_flags", {})
    missing_phase = int(blocking.get("missing_market_phase") or 0)
    known_phase = max(0, total - missing_phase)
    sessions = int(replay.get("session_count") or quality.get("session_days_observed") or 0)
    required = int(quality.get("required_live_session_days") or 5)
    downtime_rows = sum(int(float(row.get("downtime_gap_count") or 0)) > 0 for row in coverage)
    full_windows = int(quality.get("full_session_symbol_windows") or 0)
    return {
        "provider": "SSI",
        "source": "SSI_FASTCONNECT",
        "policy": "LIVE evidence only; OHLC and synthetic data never satisfy L3 session targets",
        "issues": {
            "1_price_unit": {
                "work_item": "W2.06",
                "status": "FIXED" if total and int(blocking.get("unknown_price_unit") or 0) == 0 else "BLOCKED",
                "verified_quotes": total - int(blocking.get("unknown_price_unit") or 0),
                "evidence_ref": "SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19",
            },
            "2_quantity_unit": {
                "work_item": "W2.06",
                "status": "FIXED" if total and int(blocking.get("unknown_quantity_unit") or 0) == 0 else "BLOCKED",
                "verified_quotes": total - int(blocking.get("unknown_quantity_unit") or 0),
                "evidence_ref": "SSI_CUSTOMER_SUPPORT_EMAIL_QUOTE_UNITS_FULL_BOOK_2026-11-19",
            },
            "3_market_phase": {
                "work_item": "W2.06/W2.07",
                "status": "FIXED" if total and missing_phase == 0 else "PARTIAL_LIVE" if known_phase else "BLOCKED",
                "verified_quotes": known_phase,
                "unknown_quotes": missing_phase,
                "rule": "Only a same-board SSI market.flag at-or-before quote time can set phase; no clock backfill.",
            },
            "4_simulatable_count": {
                "work_item": "W4",
                "status": "FIXED" if int(quality.get("simulatable_count") or 0) > 0 else "BLOCKED",
                "count": int(quality.get("simulatable_count") or 0),
            },
            "5_five_live_sessions": {
                "work_item": "W3.07",
                "status": "FIXED" if sessions >= required else "PENDING_FUTURE_LIVE_SESSIONS",
                "observed": sessions,
                "required": required,
                "remaining": max(0, required - sessions),
            },
            "6_full_session_gap_downtime": {
                "work_item": "W3.07/W3.09",
                "status": "FIXED" if coverage and full_windows > 0 else "REPORTING_FIXED_FULL_SESSION_PENDING" if coverage and "downtime_gap_count" in coverage[0] else "BLOCKED",
                "coverage_rows": len(coverage),
                "rows_with_downtime": downtime_rows,
                "total_detected_downtime_gaps": int(quality.get("session_downtime_gap_count") or 0),
                "full_session_windows": full_windows,
            },
            "7_multi_session_live_replay": {
                "work_item": "W3.08",
                "status": "FIXED" if sessions >= 2 else "BLOCKED",
                "session_count": sessions,
                "session_dates": [item.get("session_date") for item in replay.get("sessions", [])],
                "mode": "REPLAY preserving original_source_mode=LIVE",
            },
        },
    }


def write_status(
    quality_path: str | Path = "outputs/qa/data_quality.json",
    replay_path: str | Path = "outputs/qa/live_replay_report.json",
    coverage_path: str | Path = "outputs/qa/coverage_report.csv",
    output: str | Path = "outputs/qa/w2_w4_acceptance_status.json",
) -> dict[str, Any]:
    quality = json.loads(Path(quality_path).read_text(encoding="utf-8"))
    replay = json.loads(Path(replay_path).read_text(encoding="utf-8"))
    with Path(coverage_path).open(newline="", encoding="utf-8") as handle:
        coverage = list(csv.DictReader(handle))
    payload = build_status(quality, replay, coverage)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Consolidate the seven SSI acceptance issues.")
    parser.add_argument("--quality", default="outputs/qa/data_quality.json")
    parser.add_argument("--replay", default="outputs/qa/live_replay_report.json")
    parser.add_argument("--coverage", default="outputs/qa/coverage_report.csv")
    parser.add_argument("--output", default="outputs/qa/w2_w4_acceptance_status.json")
    args = parser.parse_args()
    payload = write_status(args.quality, args.replay, args.coverage, args.output)
    print(json.dumps(payload["issues"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
