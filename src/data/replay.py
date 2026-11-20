"""Offline replay façade. It always labels records REPLAY."""
from __future__ import annotations
from collections.abc import Iterator
from collections import defaultdict
from datetime import datetime
import argparse
import json
from pathlib import Path
from .quote_store import QuoteStore


class ReplayService:
    def __init__(self, store: QuoteStore): self.store = store
    def quotes(
        self, symbol: str | None = None, start_utc: str | None = None,
        end_utc: str | None = None, *, live_only: bool = False,
    ) -> Iterator[dict]:
        yield from self.store.replay(
            symbol, start_utc, end_utc,
            original_mode="LIVE" if live_only else None,
        )

    def live_session_report(self, symbol: str | None = None) -> list[dict]:
        """Replay every stored LIVE date without relabelling it as new LIVE data."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in self.quotes(symbol=symbol, live_only=True):
            timestamp = row.get("quote_time_vn") or row.get("received_at_utc") or "UNKNOWN"
            groups[str(timestamp)[:10].replace("/", "-")].append(row)
        report: list[dict] = []
        for session_date, rows in sorted(groups.items()):
            times = sorted(row.get("quote_time_vn") or row.get("received_at_utc") for row in rows)
            report.append({
                "session_date": session_date,
                "quote_count": len(rows),
                "symbol_count": len({row.get("symbol") for row in rows if row.get("symbol")}),
                "symbols": sorted({row.get("symbol") for row in rows if row.get("symbol")}),
                "first_quote_time": times[0] if times else None,
                "last_quote_time": times[-1] if times else None,
                "source_modes": sorted({row.get("original_source_mode") for row in rows}),
                "replay_mode": "REPLAY",
            })
        return report


def report_payload(
    sessions: list[dict], *, subscribed_symbols: list[str] | tuple[str, ...] = (),
    catalog_symbols: list[str] | tuple[str, ...] = (),
) -> dict:
    """Summarise observed evidence without pretending missing symbols emitted quotes."""
    observed = sorted({symbol for session in sessions for symbol in session.get("symbols", [])})
    subscribed = sorted({str(symbol).upper() for symbol in subscribed_symbols if symbol})
    catalog = sorted({str(symbol).upper() for symbol in catalog_symbols if symbol})
    latest = sessions[-1] if sessions else None
    return {
        "report_scope": "OBSERVED_SSI_LIVE_QUOTES_ONLY",
        "session_count": len(sessions),
        "market_catalog_stock_count": len(catalog),
        "subscribed_symbol_count": len(subscribed),
        "subscribed_symbols": subscribed,
        "observed_symbol_count": len(observed),
        "observed_symbols": observed,
        "subscribed_without_quote_count": len(set(subscribed) - set(observed)),
        "subscribed_without_quote": sorted(set(subscribed) - set(observed)),
        "latest_session_date": latest.get("session_date") if latest else None,
        "latest_session_symbol_count": latest.get("symbol_count", 0) if latest else 0,
        "sessions": sessions,
        "coverage_note": (
            "A stock appears in replay only after a real SSI QuoteMessage was persisted. "
            "Older sessions and non-emitting symbols are never backfilled from OHLC or synthetic data."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay stored SSI LIVE sessions without changing source labels.")
    parser.add_argument("--database", default="data/processed/quotes.sqlite")
    parser.add_argument("--output", default="outputs/qa/live_replay_report.json")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--collector-status", default="data/runtime/collector_status.json")
    parser.add_argument("--catalog-root", default="data/raw/rest")
    args = parser.parse_args()
    store = QuoteStore(args.database)
    try:
        report = ReplayService(store).live_session_report(args.symbol)
    finally:
        store.close()
    subscribed: list[str] = []
    try:
        status = json.loads(Path(args.collector_status).read_text(encoding="utf-8"))
        subscribed = status.get("subscriptions", []) if isinstance(status, dict) else []
    except (OSError, ValueError):
        pass
    try:
        from ssi_api.symbol_groups import catalog_equities
        catalog = list(catalog_equities(args.catalog_root))
    except (OSError, ValueError):
        catalog = []
    payload = report_payload(report, subscribed_symbols=subscribed, catalog_symbols=catalog)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({"session_count": len(report), "observed_symbol_count": payload["observed_symbol_count"], "output": args.output})


if __name__ == "__main__":
    main()
