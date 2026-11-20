import json

from app.universe import load_universe, restrict_to_latest_capture, universe_summary


def test_universe_loads_all_equity_listings_and_keeps_sector_provenance():
    rows = load_universe("data/raw/rest", "data/universe/sector_overrides.csv")
    summary = universe_summary(rows)
    # Preserve the previously observed 2,077-instrument catalogue baseline.
    # This includes warrants/ETFs/bonds; Stock is classified separately by SSI.
    assert summary["symbols"] >= 2077
    assert {row["board"] for row in rows} == {"HOSE", "HNX", "UPCOM"}
    assert next(row for row in rows if row["symbol"] == "FPT")["sector"] == "Công nghệ"
    assert next(row for row in rows if row["symbol"] == "FPT")["sector_source"] == "REVIEWED_OVERRIDE"
    # Newly collected SSI securities metadata now supplies official ICB names.
    # Missing taxonomy must remain explicit rather than assuming 2,000+ missing.
    assert summary["unclassified_sector"] == sum(row["sector"]=="UNCLASSIFIED" for row in rows)
    assert all(row["sector_source"] in {"REVIEWED_OVERRIDE","SSI_ICB","NOT_IN_SSI_MASTERDATA"} for row in rows)


def test_dashboard_universe_is_limited_to_latest_capture(tmp_path):
    rows = [
        {"symbol": "FPT", "board": "HOSE"},
        {"symbol": "AAA", "board": "HOSE"},
        {"symbol": "OUT", "board": "HNX"},
    ]
    old = {"provider": "SSI", "checked_at_utc": "2026-11-18T03:00:00Z", "symbols": ["OUT"]}
    latest = {"provider": "SSI", "checked_at_utc": "2026-11-19T03:00:00Z", "symbols": ["AAA", "FPT"]}
    (tmp_path / "ssi_capture_old.json").write_text(json.dumps(old))
    (tmp_path / "ssi_capture_latest.json").write_text(json.dumps(latest))
    scoped = restrict_to_latest_capture(rows, tmp_path)
    assert [row["symbol"] for row in scoped] == ["AAA", "FPT"]
    assert all(row["capture_scope_size"] == 2 for row in scoped)
    assert all(row["capture_date"] == "2026-11-19" for row in scoped)
