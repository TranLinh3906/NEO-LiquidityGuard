#!/usr/bin/env python3
"""Build a small, auditable SSI REPLAY bundle from the canonical local store."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from data.quote_store import QuoteStore


def latest_capture_symbols(reports_root: Path) -> tuple[list[str], str]:
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for path in reports_root.glob("ssi_capture_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        checked_at = str(payload.get("checked_at_utc") or "")
        symbols = payload.get("symbols")
        if payload.get("provider") == "SSI" and checked_at and isinstance(symbols, list) and symbols:
            candidates.append((checked_at, path, payload))
    if not candidates:
        raise RuntimeError("no valid SSI capture report")
    _, path, payload = max(candidates, key=lambda item: item[0])
    symbols = list(dict.fromkeys(str(value).strip().upper() for value in payload["symbols"] if str(value).strip()))
    return symbols, path.name


def sampled_quotes(connection: sqlite3.Connection, symbols: list[str], trade_date: str, samples: int) -> list[dict[str, Any]]:
    """Sample each symbol through the indexed symbol/time path.

    A single window query over the multi-gigabyte store forces SQLite to build a
    large temporary ranking table.  Symbol-scoped queries use
    ``idx_quotes_symbol_time`` and keep bundle generation practical.
    """
    selected: list[dict[str, Any]] = []
    for symbol in symbols:
        rows = connection.execute(
            """
            SELECT quote_json FROM quotes INDEXED BY idx_quotes_symbol_time
            WHERE symbol=? AND provider='SSI' AND source='SSI_FASTCONNECT'
              AND source_mode='LIVE' AND quote_time_vn LIKE ? AND is_simulatable=1
            ORDER BY received_at_utc, quote_id
            """,
            (symbol, f"{trade_date}%"),
        ).fetchall()
        count = len(rows)
        if not count:
            continue
        indices = sorted({round(index * (count - 1) / (samples - 1)) for index in range(min(samples, count))})
        selected.extend(json.loads(rows[index][0]) for index in indices)
    return selected


def observation_fallback(connection: sqlite3.Connection, symbol: str, trade_date: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT quote_json FROM quotes INDEXED BY idx_quotes_symbol_time
        WHERE provider='SSI' AND source='SSI_FASTCONNECT' AND source_mode='LIVE'
          AND symbol=? AND quote_time_vn LIKE ? AND is_valid_book=1
          AND json_extract(quote_json,'$.snapshot_completeness')='COMPLETE'
          AND json_extract(quote_json,'$.complete_book_verified')=1
          AND json_extract(quote_json,'$.price_unit')='VND_PER_SHARE'
          AND json_extract(quote_json,'$.quantity_unit')='SHARES'
        ORDER BY received_at_utc DESC, quote_id DESC LIMIT 1
        """,
        (symbol, f"{trade_date}%"),
    ).fetchone()
    return json.loads(row[0]) if row else None


def build(source: Path, output: Path, manifest_path: Path, reports_root: Path, *, days: int, samples: int, replace: bool) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        if not replace:
            raise FileExistsError(f"{output} exists; pass --replace")
        output.unlink()
    symbols, capture_report = latest_capture_symbols(reports_root)
    source_db = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=60)
    dates = [row[0] for row in source_db.execute(
        """SELECT DISTINCT substr(quote_time_vn,1,10) FROM quotes
           WHERE provider='SSI' AND source='SSI_FASTCONNECT' AND source_mode='LIVE'
           ORDER BY 1 DESC LIMIT ?""", (days,),
    ) if row[0]]
    dates.reverse()
    store = QuoteStore(output)
    inserted = simulatable = observation_only = 0
    observed_symbols: set[str] = set()
    per_date: dict[str, dict[str, int]] = {}
    try:
        for trade_date in dates:
            selected = sampled_quotes(source_db, symbols, trade_date, samples)
            represented = {quote["symbol"] for quote in selected}
            for symbol in symbols:
                if symbol not in represented:
                    fallback = observation_fallback(source_db, symbol, trade_date)
                    if fallback:
                        selected.append(fallback)
            date_rows = date_simulatable = date_observation = 0
            for quote in selected:
                quote["replay_bundle"] = "COMPACT_SSI_REPLAY"
                quote["replay_sampled_from_live"] = True
                quote["replay_bundle_capture_report"] = capture_report
                if store.insert(quote, commit=False):
                    inserted += 1
                    date_rows += 1
                    observed_symbols.add(str(quote.get("symbol") or ""))
                    if quote.get("is_simulatable"):
                        simulatable += 1
                        date_simulatable += 1
                    else:
                        observation_only += 1
                        date_observation += 1
            per_date[trade_date] = {"rows": date_rows, "simulatable_rows": date_simulatable, "observation_only_rows": date_observation}
        store.commit()
        store.connection.execute("VACUUM")
    finally:
        store.close()
        source_db.close()
    manifest = {
        "schema_version": "1.0", "bundle": "COMPACT_SSI_REPLAY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provider": "SSI", "source": "SSI_FASTCONNECT", "display_mode": "REPLAY", "original_source_mode": "LIVE",
        "capture_report": capture_report, "trade_dates": dates,
        "requested_symbol_count": len(symbols), "observed_symbol_count": len(observed_symbols),
        "symbols_without_rows": sorted(set(symbols) - observed_symbols),
        "samples_per_symbol_per_day": samples, "row_count": inserted,
        "simulatable_rows": simulatable, "observation_only_rows": observation_only,
        "per_date": per_date,
        "policy": "Only persisted real SSI LIVE quotes are sampled. No synthetic rows and no market-phase backfill are permitted.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/processed/quotes.sqlite"))
    parser.add_argument("--output", type=Path, default=Path("data_sample/ssi_compact_replay.sqlite"))
    parser.add_argument("--manifest", type=Path, default=Path("data_sample/ssi_compact_replay_manifest.json"))
    parser.add_argument("--reports-root", type=Path, default=Path("outputs/qa"))
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--samples-per-symbol", type=int, default=12)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.days < 1 or args.samples_per_symbol < 2:
        parser.error("--days must be >=1 and --samples-per-symbol must be >=2")
    print(json.dumps(build(args.source, args.output, args.manifest, args.reports_root, days=args.days, samples=args.samples_per_symbol, replace=args.replace), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
