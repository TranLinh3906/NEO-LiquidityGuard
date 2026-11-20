"""Missing, stale, partial, provenance and gap summaries for SSI canonical quotes."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from .quote_store import QuoteStore
from .coverage_report import session_metrics, _masterdata_board_map


BOOK_FIELDS = tuple(
    f"{side}_{kind}_{level}"
    for side in ("bid", "ask") for kind in ("price", "qty") for level in range(1, 4)
)


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=7)))


def write_quality_report(
    store: QuoteStore, output: str | Path, *, gap_threshold_seconds: float = 60,
) -> dict:
    rows = list(store.records())
    total = len(rows)
    missing = sum(row.get(field) is None for row in rows for field in BOOK_FIELDS)
    hashes = [row.get("payload_hash") for row in rows if row.get("payload_hash")]
    ordered = sorted(rows, key=lambda row: (row.get("symbol") or "", row.get("received_at_utc") or ""))
    gaps: list[float] = []
    for previous, current in zip(ordered, ordered[1:]):
        if previous.get("symbol") == current.get("symbol") and previous.get("received_at_utc") and current.get("received_at_utc"):
            seconds = (_parse_time(current["received_at_utc"]) - _parse_time(previous["received_at_utc"])).total_seconds()
            if seconds > gap_threshold_seconds:
                gaps.append(seconds)

    flag_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    update_counts: Counter[str] = Counter()
    simulatable_modes: Counter[str] = Counter()
    session_groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        flag_counts.update(row.get("quality_flags", []))
        mode_counts.update([row.get("source_mode") or "UNKNOWN"])
        update_counts.update([row.get("update_type") or "UNKNOWN"])
        if row.get("is_simulatable"):
            simulatable_modes.update([row.get("source_mode") or "UNKNOWN"])
        observed = row.get("quote_time_vn") or row.get("received_at_utc")
        if observed:
            session_groups.setdefault((str(observed)[:10], str(row.get("symbol") or "UNKNOWN")), []).append(row)

    board_map = _masterdata_board_map()
    session_summaries = []
    for (trade_date, symbol), group in session_groups.items():
        parsed = [_parse_time(row.get("quote_time_vn") or row.get("received_at_utc")) for row in group]
        parsed = [value for value in parsed if value is not None]
        session_summaries.append(session_metrics(parsed, board=board_map.get(symbol, "UNKNOWN")))

    valid_count = sum(bool(row.get("is_valid_book")) for row in rows)
    simulatable_count = sum(bool(row.get("is_simulatable")) for row in rows)
    provenance_errors = sum(
        row.get("provider") != "SSI" or row.get("source") != "SSI_FASTCONNECT"
        for row in rows
    )
    report = {
        "provider": "SSI", "source": "SSI_FASTCONNECT", "report_mode": "STORED_ORIGINAL",
        "quote_count": total,
        "symbol_count": len({row.get("symbol") for row in rows if row.get("symbol")}),
        "mode_counts": dict(mode_counts), "update_type_counts": dict(update_counts),
        "valid_book_count": valid_count,
        "valid_book_ratio": valid_count / total if total else None,
        "simulatable_count": simulatable_count,
        "simulatable_ratio": simulatable_count / total if total else None,
        "simulatable_count_by_mode": dict(simulatable_modes),
        "w4_live_gate": {
            "status": "OPEN" if simulatable_count else "CLOSED_LIVE",
            "blocking_flags": {
                "unknown_price_unit": flag_counts.get("UNKNOWN_PRICE_UNIT", 0),
                "unknown_quantity_unit": flag_counts.get("UNKNOWN_QTY_UNIT", 0),
                "missing_market_phase": flag_counts.get("MISSING_MARKET_PHASE", 0),
            },
            "note": "LIVE eligibility is not promoted without SSI unit evidence and a same-board market.flag join.",
        },
        "complete_snapshot_count": sum(row.get("snapshot_completeness") == "COMPLETE" for row in rows),
        "partial_update_count": sum(row.get("update_type") == "PARTIAL_BOOK" for row in rows),
        "missing_book_field_count": missing,
        "missing_book_field_ratio": missing / (total * len(BOOK_FIELDS)) if total else None,
        "repeated_payload_hash_count": len(hashes) - len(set(hashes)),
        "note_on_hashes": "Repeated payload hashes are QA signals, not automatic duplicates.",
        "provenance_error_count": provenance_errors,
        "stale_count": sum(bool(row.get("is_stale")) for row in rows),
        "gap_threshold_seconds": gap_threshold_seconds,
        "gap_count": len(gaps), "max_gap_seconds": max(gaps, default=None),
        "first_received_at_utc": min((row.get("received_at_utc") for row in rows if row.get("received_at_utc")), default=None),
        "last_received_at_utc": max((row.get("received_at_utc") for row in rows if row.get("received_at_utc")), default=None),
        "flag_counts": dict(flag_counts),
        "session_days_observed": len({key[0] for key in session_groups}),
        "required_live_session_days": 5,
        "missing_live_session_days_to_target": max(0, 5 - len({key[0] for key in session_groups})),
        "session_symbol_windows": len(session_groups),
        "full_session_symbol_windows": sum(item["session_status"] == "FULL_SESSION" for item in session_summaries),
        "full_session_days_observed": len({key[0] for key, item in zip(session_groups, session_summaries) if item["session_status"] == "FULL_SESSION"}),
        "missing_full_session_days_to_target": max(0, 5 - len({key[0] for key, item in zip(session_groups, session_summaries) if item["session_status"] == "FULL_SESSION"})),
        "session_downtime_gap_count": sum(item["downtime_gap_count"] for item in session_summaries),
        "max_session_downtime_seconds": max((item["max_downtime_seconds"] for item in session_summaries), default=0),
        "sample_label_integrity": {
            "synthetic_count": mode_counts.get("SYNTHETIC_TEST", 0),
            "live_count": mode_counts.get("LIVE", 0),
            "replay_is_view_only": True,
        },
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Report SSI canonical quote quality using original evidence labels.")
    parser.add_argument("--database", default="data/processed/quotes.sqlite")
    parser.add_argument("--output", default="outputs/qa/data_quality.json")
    parser.add_argument("--gap-threshold-seconds", type=float, default=60)
    args = parser.parse_args()
    store = QuoteStore(args.database)
    try:
        report = write_quality_report(store, args.output, gap_threshold_seconds=args.gap_threshold_seconds)
        print({"quote_count": report["quote_count"], "output": args.output})
    finally:
        store.close()


if __name__ == "__main__":
    main()
