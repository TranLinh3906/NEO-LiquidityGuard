"""Derived liquidity mart built from canonical SSI L3 quotes only."""
from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any

from finance.liquidity import liquidity_metrics
from .quote_store import QuoteStore


def _scalar(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


class LiquidityMart:
    def __init__(self, path: str | Path = "data/mart/liquidity.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS liquidity_metrics (
          quote_id TEXT PRIMARY KEY, raw_event_id TEXT NOT NULL, provider TEXT NOT NULL,
          source TEXT NOT NULL, original_source_mode TEXT NOT NULL, symbol TEXT,
          received_at_utc TEXT NOT NULL, quote_time_vn TEXT, is_eligible INTEGER NOT NULL,
          rejection_reasons TEXT NOT NULL, spread_abs TEXT, mid_price TEXT, spread_pct TEXT,
          spread_bps TEXT, bid_depth_3 TEXT, ask_depth_3 TEXT, bid_notional_3 TEXT,
          ask_notional_3 TEXT, obi_3 TEXT)""")
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_mart_symbol_time ON liquidity_metrics(symbol, received_at_utc)"
        )
        self.connection.commit()

    def insert(self, quote: dict[str, Any]) -> bool:
        metrics = liquidity_metrics(quote)
        columns = (
            "quote_id", "raw_event_id", "provider", "source", "original_source_mode",
            "symbol", "received_at_utc", "quote_time_vn", "is_eligible",
            "rejection_reasons", "spread_abs", "mid_price", "spread_pct", "spread_bps",
            "bid_depth_3", "ask_depth_3", "bid_notional_3", "ask_notional_3", "obi_3",
        )
        values = (
            quote["quote_id"], quote["raw_event_id"], quote.get("provider", "SSI"),
            quote.get("source", "SSI_FASTCONNECT"), quote.get("source_mode", "UNKNOWN"),
            quote.get("symbol"), quote["received_at_utc"], quote.get("quote_time_vn"),
            int(bool(metrics["is_eligible"])), json.dumps(metrics["rejection_reasons"]),
            *(_scalar(metrics[name]) for name in (
                "spread_abs", "mid_price", "spread_pct", "spread_bps", "bid_depth_3",
                "ask_depth_3", "bid_notional_3", "ask_notional_3", "obi_3",
            )),
        )
        try:
            self.connection.execute(
                f"INSERT INTO liquidity_metrics ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                values,
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def close(self) -> None:
        self.connection.close()


def build_liquidity_mart(source: QuoteStore, mart: LiquidityMart) -> dict[str, int]:
    counts = {"canonical_quotes": 0, "mart_inserted": 0, "mart_existing": 0}
    for quote in source.records():
        counts["canonical_quotes"] += 1
        inserted = mart.insert(quote)
        counts["mart_inserted"] += int(inserted)
        counts["mart_existing"] += int(not inserted)
    return counts


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build an idempotent liquidity mart from canonical SSI L3 quotes.")
    parser.add_argument("--database", default="data/processed/quotes.sqlite")
    parser.add_argument("--mart", default="data/mart/liquidity.sqlite")
    args = parser.parse_args()
    source, mart = QuoteStore(args.database), LiquidityMart(args.mart)
    try:
        print(build_liquidity_mart(source, mart))
    finally:
        mart.close()
        source.close()


if __name__ == "__main__":
    main()
