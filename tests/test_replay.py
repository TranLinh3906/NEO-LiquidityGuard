import json

from data.normalize_quotes import normalise_envelope
from data.pipeline import process
from data.quote_store import QuoteStore
from data.replay import ReplayService, report_payload


def raw_quote(event_id: str = "event-a") -> dict:
    return {
        "raw_event_id": event_id, "provider": "SSI", "source": "SSI_FASTCONNECT",
        "mode": "SYNTHETIC_TEST", "transport": "WS", "endpoint_or_channel": "quote",
        "received_at_utc": "2026-11-09T03:00:00.000Z", "payload_hash": "x",
        "payload": {
            "type": "quote", "symbol": "SSI", "trading_time": "2026-11-09T10:00:00+07:00",
            "bid_prices": [30000, 29950, 29900], "bid_volumes": [10, 9, 8],
            "ask_prices": [30050, 30100, 30150], "ask_volumes": [7, 6, 5],
        },
    }


def test_replay_filters_symbol_and_never_claims_live(tmp_path):
    store = QuoteStore(tmp_path / "quotes.sqlite")
    store.insert(normalise_envelope(raw_quote())[0])
    rows = list(ReplayService(store).quotes("SSI"))
    assert len(rows) == 1 and rows[0]["source_mode"] == "REPLAY"
    assert rows[0]["original_source_mode"] == "SYNTHETIC_TEST"
    assert rows[0]["provider"] == "SSI" and rows[0]["source"] == "SSI_FASTCONNECT"
    assert list(ReplayService(store).quotes("HPG")) == []
    store.close()


def test_processing_same_raw_file_twice_is_idempotent(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    raw_path.write_text(json.dumps(raw_quote("event-repeat")) + "\n", encoding="utf-8")
    store = QuoteStore(tmp_path / "quotes.sqlite")
    assert process([raw_path], store)["quotes_inserted"] == 1
    rerun = process([raw_path], store)
    assert rerun["quotes_inserted"] == 0 and rerun["quotes_existing"] == 1
    assert len(list(store.replay())) == 1
    store.close()


def test_explicit_renormalisation_updates_same_raw_lineage(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    raw_path.write_text(json.dumps(raw_quote("evidence-event")) + "\n", encoding="utf-8")
    store = QuoteStore(tmp_path / "quotes.sqlite")
    process([raw_path], store)
    result = process(
        [raw_path], store, price_multiplier_to_vnd=1,
        quantity_multiplier_to_shares=1, unit_evidence_ref="SSI_SUPPORT_EMAIL_2026-11-19",
        complete_book_verified=True, allowed_phases={"LO"}, replace_existing=True,
    )
    assert result["quotes_updated"] == 1 and result["quotes_inserted"] == 0
    row = next(store.records())
    assert row["price_unit"] == "VND_PER_SHARE" and row["quantity_unit"] == "SHARES"
    assert row["unit_evidence_ref"] == "SSI_SUPPORT_EMAIL_2026-11-19"
    assert row["complete_book_verified"] is True
    store.close()


def test_collector_restart_reopens_same_store_without_duplicate_history(tmp_path):
    raw_path = tmp_path / "raw.jsonl"
    raw_path.write_text(json.dumps(raw_quote("restart-event")) + "\n", encoding="utf-8")
    database = tmp_path / "quotes.sqlite"
    first_store = QuoteStore(database)
    assert process([raw_path], first_store)["quotes_inserted"] == 1
    first_store.close()
    restarted_store = QuoteStore(database)
    assert process([raw_path], restarted_store)["quotes_inserted"] == 0
    assert len(list(ReplayService(restarted_store).quotes("SSI"))) == 1
    restarted_store.close()


def test_two_same_second_updates_are_both_kept(tmp_path):
    first, second = raw_quote("event-1"), raw_quote("event-2")
    second["payload_hash"] = "y"
    second["payload"]["bid_volumes"][0] = 11
    raw_path = tmp_path / "updates.jsonl"
    raw_path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    store = QuoteStore(tmp_path / "quotes.sqlite")
    result = process([raw_path], store)
    assert result["quotes_inserted"] == 2
    assert len(list(store.records())) == 2
    store.close()


def test_partial_update_never_forward_fills_previous_levels(tmp_path):
    first = raw_quote("event-full")
    second = raw_quote("event-partial")
    second["payload_hash"] = "partial-hash"
    second["payload"]["ask_prices"] = [30050]
    second["payload"]["ask_volumes"] = [7]
    raw_path = tmp_path / "partial.jsonl"
    raw_path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    store = QuoteStore(tmp_path / "quotes.sqlite")
    result = process([raw_path], store)
    assert result["full_book_records"] == 1 and result["partial_book_records"] == 1
    rows = list(store.records())
    partial = next(row for row in rows if row["raw_event_id"] == "event-partial")
    assert partial["update_type"] == "PARTIAL_BOOK"
    assert partial["ask_price_2"] is None and partial["ask_qty_2"] is None
    assert partial["partial_update_policy"] == "PRESERVE_NO_MERGE"
    store.close()


def test_live_only_replay_excludes_synthetic_samples(tmp_path):
    store = QuoteStore(tmp_path / "quotes.sqlite")
    synthetic = normalise_envelope(raw_quote())[0]
    live_raw = raw_quote("live-event"); live_raw["mode"] = "LIVE"
    store.insert(synthetic); store.insert(normalise_envelope(live_raw)[0])
    rows = list(ReplayService(store).quotes("SSI", live_only=True))
    assert len(rows) == 1 and rows[0]["original_source_mode"] == "LIVE"
    store.close()


def test_live_replay_reports_multiple_session_dates(tmp_path):
    store = QuoteStore(tmp_path / "quotes.sqlite")
    first = raw_quote("live-1"); first["mode"] = "LIVE"; first["payload"]["trading_time"] = "2026-11-09T10:00:00+07:00"
    second = raw_quote("live-2"); second["mode"] = "LIVE"; second["payload"]["trading_time"] = "2026-11-10T10:00:00+07:00"
    store.insert(normalise_envelope(first)[0]); store.insert(normalise_envelope(second)[0])
    report = ReplayService(store).live_session_report()
    assert [row["session_date"] for row in report] == ["2026-11-09", "2026-11-10"]
    assert all(row["replay_mode"] == "REPLAY" and row["source_modes"] == ["LIVE"] for row in report)
    assert all(row["symbol_count"] == 1 for row in report)
    payload = report_payload(report, subscribed_symbols=["SSI", "FPT"], catalog_symbols=["SSI", "FPT", "VPB"])
    assert payload["market_catalog_stock_count"] == 3
    assert payload["subscribed_symbol_count"] == 2
    assert payload["observed_symbol_count"] == 1
    assert payload["subscribed_without_quote"] == ["FPT"]
    store.close()
