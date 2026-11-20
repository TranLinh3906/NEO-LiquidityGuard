from data.coverage_report import write_coverage_report
from data.normalize_quotes import normalise_envelope
from data.quality_report import write_quality_report
from data.quote_store import QuoteStore


def test_quality_and_coverage_reports_are_quantitative(tmp_path):
    raw = {
        "raw_event_id": "qa-event", "provider": "SSI", "source": "SSI_FASTCONNECT",
        "mode": "SYNTHETIC_TEST", "transport": "WS", "endpoint_or_channel": "quote",
        "received_at_utc": "2026-11-09T03:00:00.000Z", "payload_hash": "hash",
        "payload": {
            "type": "quote", "symbol": "SSI", "market_phase": "LO",
            "trading_time": "2026-11-09T10:00:00+07:00",
            "bid_prices": [30000, 29950, 29900], "bid_volumes": [1, 1, 1],
            "ask_prices": [30050, 30100, 30150], "ask_volumes": [1, 1, 1],
        },
    }
    store = QuoteStore(tmp_path / "quotes.sqlite")
    store.insert(normalise_envelope(
        raw, price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"},
    )[0])
    quality = write_quality_report(store, tmp_path / "quality.json")
    coverage = write_coverage_report(store, tmp_path / "coverage.csv")
    assert quality["quote_count"] == quality["valid_book_count"] == 1
    assert quality["missing_book_field_count"] == quality["repeated_payload_hash_count"] == 0
    assert quality["mode_counts"] == {"SYNTHETIC_TEST": 1}
    assert quality["update_type_counts"] == {"FULL_BOOK": 1}
    assert coverage[0]["trade_date"] == "2026-11-09" and coverage[0]["symbol"] == "SSI"
    assert coverage[0]["coverage_status"] == "OBSERVED_ONLY"
    assert coverage[0]["session_windows_expected"] == 2
    assert coverage[0]["missing_session_seconds"] > 0
    store.close()
