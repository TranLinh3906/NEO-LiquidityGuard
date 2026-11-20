import asyncio
import json

from data.collector import RawCollector
from data.collector_status import CollectorStatus
from data.raw_writer import RawWriter


async def messages():
    yield {"type": "quote", "symbol": "SSI", "trading_time": "2026-11-09T10:00:00+07:00"}
    yield {"type": "quote", "symbol": "HPG", "trading_time": "2026-11-09T10:00:01+07:00"}


def test_collector_writes_messages_and_status(tmp_path):
    status_path = tmp_path / "collector_status.json"
    collector = RawCollector(RawWriter(tmp_path / "raw"), CollectorStatus(), str(status_path), "session-1", ["SSI", "HPG"])
    assert asyncio.run(collector.collect(messages())) == 2
    status = json.loads(status_path.read_text())
    assert status["state"] == "online" and status["message_count"] == 2
    assert status["quote_count"] == 2 and status["last_quote_at_utc"] is not None
    output = next((tmp_path / "raw" / "ws").glob("*.jsonl"))
    assert len(output.read_text().splitlines()) == 2
    first = json.loads(output.read_text().splitlines()[0])
    assert first["provider"] == "SSI" and first["endpoint_or_channel"] == "quote"
