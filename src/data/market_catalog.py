"""Store genuine daily SSI market summaries separately from L3 quotes."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def normalize_summary(row):
    def field(*names):
        return next((row[name] for name in names if name in row), None)
    return {
        "symbol": str(field("symbol") or "").upper(),
        "trading_date": field("tradingDate", "trading_date"),
        "close": field("close", "close_price"), "open": field("open", "open_price"),
        "high": field("high", "high_price"), "low": field("low", "low_price"),
        "volume": field("totalMatch", "total_match", "volume"),
        "value": field("totalMatchValue", "total_match_value", "value"),
        "price_change": field("priceChange", "price_change"),
        "price_change_pct": field("priceChangePercentage", "price_change_percentage", "price_change_percent"),
        "provider": "SSI", "source": "SSI_FASTCONNECT", "source_mode": "HISTORICAL_REST",
    }


def save_summaries(rows, path="data/processed/market_catalog.sqlite", *, raw_event_id=None, received_at_utc=None):
    destination=Path(path); destination.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with sqlite3.connect(destination) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS market_daily (symbol TEXT NOT NULL, trading_date TEXT NOT NULL, record_json TEXT NOT NULL, PRIMARY KEY(symbol,trading_date))")
        for source in rows:
            row=normalize_summary(source)
            if not row["symbol"] or not row["trading_date"]: continue
            row.update(raw_event_id=raw_event_id, received_at_utc=received_at_utc or datetime.now(timezone.utc).isoformat())
            connection.execute("INSERT INTO market_daily VALUES (?,?,?) ON CONFLICT(symbol,trading_date) DO UPDATE SET record_json=excluded.record_json",(row["symbol"],row["trading_date"],json.dumps(row,ensure_ascii=False)))
            count+=1
    return count


def rebuild_from_raw(paths,path="data/processed/market_catalog.sqlite"):
    count=0
    for source in paths:
        with Path(source).open(encoding="utf-8") as handle:
            for line in handle:
                if 'securitiesSummary' not in line:continue
                event=json.loads(line)
                if event.get("endpoint_or_channel")!="/api/v3/data/securitiesSummary":continue
                payload=event.get("payload")
                rows=payload.get("data",[]) if isinstance(payload,dict) else payload if isinstance(payload,list) else []
                count+=save_summaries(rows,path,raw_event_id=event.get("raw_event_id"),received_at_utc=event.get("received_at_utc"))
    return count


def load_latest(path="data/processed/market_catalog.sqlite"):
    path=Path(path)
    if not path.exists(): return {}
    with sqlite3.connect(f"file:{path}?mode=ro",uri=True) as connection:
        data=connection.execute("SELECT d.record_json FROM market_daily d JOIN (SELECT symbol,MAX(trading_date) last_date FROM market_daily GROUP BY symbol) m ON m.symbol=d.symbol AND m.last_date=d.trading_date").fetchall()
    return {row["symbol"]:row for (raw,) in data if (row:=json.loads(raw))}


def load_symbol(symbol,path="data/processed/market_catalog.sqlite"):
    path=Path(path)
    if not path.exists(): return []
    with sqlite3.connect(f"file:{path}?mode=ro",uri=True) as connection:
        return [json.loads(row[0]) for row in connection.execute("SELECT record_json FROM market_daily WHERE symbol=? ORDER BY trading_date",(symbol.upper(),))]
