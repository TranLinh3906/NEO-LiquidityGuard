import json

import pytest

from ssi_api.symbol_groups import VN30_SYMBOLS, catalog_equities, resolve_symbols


def test_vn30_is_complete_and_replaces_two_symbol_fallback():
    assert len(VN30_SYMBOLS) == 30
    assert {"FPT", "VPB", "SSI", "HPG", "VCB"} <= set(VN30_SYMBOLS)
    assert resolve_symbols("VN30") == VN30_SYMBOLS
    assert resolve_symbols("WATCHLIST") == VN30_SYMBOLS


def test_explicit_watchlist_remains_supported():
    assert resolve_symbols("WATCHLIST", [" fpt ", "VPB", "fpt"]) == ("FPT", "VPB")
    assert resolve_symbols("VN30", ["MBB", "TCB"]) == ("MBB", "TCB")


def test_all_scope_reads_only_stocks_from_saved_ssi_catalog(tmp_path):
    root = tmp_path / "rest"
    root.mkdir()
    event = {
        "endpoint_or_channel": "/api/v3/data/securitiesByBoard",
        "received_at_utc": "2026-11-18T01:00:00Z",
        "payload": {"data": [
            {"symbol": "FPT", "stock_type": "Stock", "board": "HOSE"},
            {"symbol": "ACB", "stockType": "Stock", "board": "HOSE"},
            {"symbol": "CFPT2510", "stock_type": "CW Product", "board": "HOSE"},
        ]},
    }
    (root / "capture.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    assert catalog_equities(root) == ("ACB", "FPT")
    assert resolve_symbols("ALL", ["VPB"], raw_root=root) == ("ACB", "FPT")


def test_all_scope_refuses_to_fake_catalog(tmp_path):
    with pytest.raises(ValueError, match="securitiesByBoard"):
        resolve_symbols("ALL", raw_root=tmp_path)
