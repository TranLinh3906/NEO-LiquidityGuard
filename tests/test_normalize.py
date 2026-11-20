from copy import deepcopy

from data.normalize_quotes import normalise_envelope


def envelope(*, complete: bool = True, mode: str = "SYNTHETIC_TEST") -> dict:
    payload = {
        "type": "quote", "trading_time": "2026-11-09T10:00:00+07:00",
        "symbol": "ssi", "market_phase": "LO",
        "bid_prices": [30000, 29950, 29900], "bid_volumes": [1000, 800, 600],
        "ask_prices": [30050, 30100, 30150], "ask_volumes": [900, 1100, 1200],
    }
    if not complete:
        payload["ask_prices"] = payload["ask_prices"][:1]
    return {
        "raw_event_id": "evt-ssi-1", "provider": "SSI", "source": "SSI_FASTCONNECT",
        "mode": mode, "transport": "WS", "endpoint_or_channel": "quote",
        "received_at_utc": "2026-11-09T03:00:00.000Z",
        "provider_timestamp_raw": payload["trading_time"], "payload_hash": "hash",
        "payload": payload,
    }


def test_ssi_quote_normalises_and_keeps_synthetic_label():
    quote = normalise_envelope(envelope(), allowed_phases={"LO"})[0]
    assert quote["symbol"] == "SSI"
    assert quote["snapshot_completeness"] == "COMPLETE"
    assert quote["update_type"] == "FULL_BOOK" and quote["book_level_count"] == 3
    assert quote["partial_update_policy"] == "PRESERVE_NO_MERGE"
    assert quote["source_mode"] == "SYNTHETIC_TEST"
    assert not quote["is_simulatable"]


def test_concrete_units_open_the_synthetic_formula_gate():
    quote = normalise_envelope(
        envelope(), price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"},
    )[0]
    assert quote["price_unit"] == "VND_PER_SHARE"
    assert quote["quantity_unit"] == "SHARES"
    assert quote["is_simulatable"]


def test_non_numeric_quote_price_is_not_coerced_to_zero():
    raw = deepcopy(envelope())
    raw["payload"]["ask_prices"][0] = "ATO"
    quote = normalise_envelope(raw)[0]
    assert quote["ask_price_1"] is None
    assert "NON_NUMERIC_ASK_PRICE" in quote["quality_flags"]


def test_incomplete_quote_is_not_assumed_complete():
    quote = normalise_envelope(envelope(complete=False))[0]
    assert quote["snapshot_completeness"] == "UNKNOWN"
    assert quote["update_type"] == "PARTIAL_BOOK"
    assert quote["ask_price_2"] is None and quote["ask_price_3"] is None
    assert "UNKNOWN_SNAPSHOT_SEMANTICS" in quote["quality_flags"]


def test_non_quote_rest_payload_is_not_a_canonical_order_book():
    raw = envelope()
    raw.update({"transport": "REST", "endpoint_or_channel": "/api/v3/data/masterdata"})
    raw["payload"] = {"symbol": "SSI", "ref_price": 30000}
    assert normalise_envelope(raw) == []


def test_neo_lineage_is_rejected_in_ssi_only_pipeline():
    raw = envelope()
    raw["provider"] = "NEO"
    raw["source"] = "NEO_API"
    quote = normalise_envelope(raw)[0]
    assert "UNEXPECTED_PROVIDER" in quote["quality_flags"]
    assert "UNEXPECTED_SOURCE" in quote["quality_flags"]
    assert not quote["is_valid_book"]


def test_old_live_quote_is_flagged_stale():
    raw = envelope()
    raw["received_at_utc"] = "2026-11-09T03:00:10Z"
    raw["provider_timestamp_raw"] = "2026-11-09T10:00:00+07:00"
    quote = normalise_envelope(raw, stale_after_seconds=5)[0]
    assert quote["is_stale"]
    assert "STALE" in quote["quality_flags"]


def test_ssi_local_timestamp_is_parsed_as_vietnam_time():
    raw = envelope()
    raw["provider_timestamp_raw"] = "2026/11/16 13:41:47"
    raw["payload"]["trading_time"] = raw["provider_timestamp_raw"]
    raw["received_at_utc"] = "2026-11-16T06:41:47Z"
    quote = normalise_envelope(raw, stale_after_seconds=5)[0]
    assert quote["arrival_delay_seconds"] == 0
    assert "STALE" not in quote["quality_flags"]
