"""SQLite storage for canonical quotes; raw JSONL remains the system of record."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator

QUOTE_COLUMNS = (
    "quote_id", "raw_event_id", "symbol", "provider", "source",
    "source_type", "source_mode", "received_at_utc", "quote_time_vn",
    "market_phase", "snapshot_completeness", "update_type", "connection_id",
    "sequence_no", "is_valid_book", "is_simulatable", "quality_flags", "payload_hash",
)


class QuoteStore:
    def __init__(self, path: str | Path = "data/processed/quotes.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS quotes (
          quote_id TEXT PRIMARY KEY, raw_event_id TEXT NOT NULL, symbol TEXT,
          provider TEXT, source TEXT, source_type TEXT, source_mode TEXT,
          received_at_utc TEXT NOT NULL, quote_time_vn TEXT, market_phase TEXT,
          snapshot_completeness TEXT NOT NULL, update_type TEXT, connection_id TEXT,
          sequence_no INTEGER, is_valid_book INTEGER NOT NULL, is_simulatable INTEGER NOT NULL,
          quality_flags TEXT NOT NULL, payload_hash TEXT,
          quote_json TEXT NOT NULL)""")
        existing = {row[1] for row in self.connection.execute("PRAGMA table_info(quotes)")}
        migrations = {
            "provider": "TEXT", "source": "TEXT", "quote_time_vn": "TEXT",
            "update_type": "TEXT", "connection_id": "TEXT", "sequence_no": "INTEGER",
        }
        for column, sql_type in migrations.items():
            if column not in existing:
                self.connection.execute(f"ALTER TABLE quotes ADD COLUMN {column} {sql_type}")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_quotes_symbol_time ON quotes(symbol, received_at_utc)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_quotes_provider_source_mode ON quotes(provider, source, source_mode)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_quotes_connection_sequence ON quotes(connection_id, sequence_no)")
        self.connection.commit()

    def insert(self, quote: dict[str, Any], *, commit: bool = True) -> bool:
        stored = {column: quote.get(column) for column in QUOTE_COLUMNS}
        stored["is_valid_book"] = int(bool(stored["is_valid_book"]))
        stored["is_simulatable"] = int(bool(stored["is_simulatable"]))
        stored["quality_flags"] = json.dumps(stored["quality_flags"])
        values = [stored[column] for column in QUOTE_COLUMNS]
        try:
            self.connection.execute(f"INSERT INTO quotes ({','.join(QUOTE_COLUMNS)},quote_json) VALUES ({','.join('?' for _ in range(len(QUOTE_COLUMNS) + 1))})", (*values, json.dumps(quote, ensure_ascii=False)))
            if commit:
                self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, quote: dict[str, Any], *, commit: bool = True) -> bool:
        """Replace canonical fields while preserving immutable raw lineage."""
        stored = {column: quote.get(column) for column in QUOTE_COLUMNS}
        stored["is_valid_book"] = int(bool(stored["is_valid_book"]))
        stored["is_simulatable"] = int(bool(stored["is_simulatable"]))
        stored["quality_flags"] = json.dumps(stored["quality_flags"])
        assignments = ",".join(f"{column}=?" for column in QUOTE_COLUMNS[1:])
        values = [stored[column] for column in QUOTE_COLUMNS[1:]]
        cursor = self.connection.execute(
            f"UPDATE quotes SET {assignments},quote_json=? WHERE quote_id=?",
            (*values, json.dumps(quote, ensure_ascii=False), stored["quote_id"]),
        )
        if commit:
            self.connection.commit()
        return bool(cursor.rowcount)

    def commit(self) -> None:
        self.connection.commit()

    def records(
        self, symbol: str | None = None, start_utc: str | None = None,
        end_utc: str | None = None, *, provider: str | None = "SSI",
        source: str | None = "SSI_FASTCONNECT", original_mode: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        conditions, values = [], []
        if symbol: conditions.append("symbol = ?"); values.append(symbol.upper())
        if start_utc: conditions.append("received_at_utc >= ?"); values.append(start_utc)
        if end_utc: conditions.append("received_at_utc <= ?"); values.append(end_utc)
        if provider: conditions.append("provider = ?"); values.append(provider)
        if source: conditions.append("source = ?"); values.append(source)
        if original_mode: conditions.append("source_mode = ?"); values.append(original_mode.upper())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        for (encoded,) in self.connection.execute("SELECT quote_json FROM quotes" + where + " ORDER BY received_at_utc, quote_id", values):
            yield json.loads(encoded)

    def replay(
        self, symbol: str | None = None, start_utc: str | None = None,
        end_utc: str | None = None, *, original_mode: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        for quote in self.records(symbol, start_utc, end_utc, original_mode=original_mode):
            quote["original_source_mode"] = quote.get("source_mode")
            quote["source_mode"] = "REPLAY"
            yield quote

    def close(self) -> None:
        self.connection.close()
