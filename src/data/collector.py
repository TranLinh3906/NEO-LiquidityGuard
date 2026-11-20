"""Independent WebSocket message collector; it has no UI dependency."""
from __future__ import annotations

from collections.abc import AsyncIterable
from typing import Any

from .collector_status import CollectorStatus
from .raw_writer import RawWriter


class RawCollector:
    def __init__(self, writer: RawWriter, status: CollectorStatus, status_path: str, connection_id: str, symbols: list[str], *, mode: str = "SYNTHETIC_TEST"):
        self.writer, self.status, self.status_path = writer, status, status_path
        self.connection_id, self.symbols, self.mode, self.sequence_no = connection_id, symbols, mode, 0

    async def collect(self, messages: AsyncIterable[dict[str, Any]]) -> int:
        self.status.connected(self.connection_id, self.symbols)
        self.status.save(self.status_path)
        try:
            async for payload in messages:
                self.sequence_no += 1
                symbol = payload.get("symbol") if isinstance(payload, dict) else None
                self.writer.write(
                    provider="SSI", source="SSI_FASTCONNECT", mode=self.mode,
                    transport="WS", endpoint_or_channel="quote", payload=payload,
                    symbol_hint=symbol, provider_timestamp_raw=payload.get("trading_time"),
                    connection_id=self.connection_id, sequence_no=self.sequence_no,
                )
                self.status.quote_received()
                self.status.save(self.status_path)
        except Exception as exc:
            self.status.failed(exc)
            self.status.save(self.status_path)
            raise
        return self.sequence_no
"""Market data collector."""
