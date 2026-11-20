from data.mart import LiquidityMart, build_liquidity_mart
from data.normalize_quotes import normalise_envelope
from data.quote_store import QuoteStore


def test_mart_is_derived_from_canonical_quotes_and_is_idempotent(tmp_path):
    raw = {
        "raw_event_id": "mart-event", "provider": "SSI", "source": "SSI_FASTCONNECT",
        "mode": "SYNTHETIC_TEST", "transport": "WS", "endpoint_or_channel": "quote",
        "received_at_utc": "2026-11-09T03:00:00Z", "payload_hash": "hash",
        "payload": {
            "type": "quote", "symbol": "SSI", "market_phase": "LO",
            "trading_time": "2026-11-09T10:00:00+07:00",
            "bid_prices": [30000, 29950, 29900], "bid_volumes": [10, 9, 8],
            "ask_prices": [30050, 30100, 30150], "ask_volumes": [7, 6, 5],
        },
    }
    source = QuoteStore(tmp_path / "quotes.sqlite")
    source.insert(normalise_envelope(
        raw, price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"},
    )[0])
    mart = LiquidityMart(tmp_path / "mart.sqlite")
    first = build_liquidity_mart(source, mart)
    second = build_liquidity_mart(source, mart)
    assert first == {"canonical_quotes": 1, "mart_inserted": 1, "mart_existing": 0}
    assert second == {"canonical_quotes": 1, "mart_inserted": 0, "mart_existing": 1}
    row = mart.connection.execute("SELECT provider, source, symbol, is_eligible FROM liquidity_metrics").fetchone()
    assert row == ("SSI", "SSI_FASTCONNECT", "SSI", 1)
    mart.close(); source.close()
