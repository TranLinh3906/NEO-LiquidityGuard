from data.acceptance_status import build_status


def test_acceptance_status_separates_fixed_items_from_future_live_evidence():
    quality = {
        "quote_count": 100,
        "simulatable_count": 20,
        "required_live_session_days": 5,
        "session_days_observed": 3,
        "session_downtime_gap_count": 7,
        "full_session_symbol_windows": 0,
        "w4_live_gate": {"blocking_flags": {
            "unknown_price_unit": 0,
            "unknown_quantity_unit": 0,
            "missing_market_phase": 80,
        }},
    }
    replay = {"session_count": 3, "sessions": [
        {"session_date": "2026-11-16"},
        {"session_date": "2026-11-18"},
        {"session_date": "2026-11-19"},
    ]}
    coverage = [{"downtime_gap_count": "2"}]
    issues = build_status(quality, replay, coverage)["issues"]
    assert issues["1_price_unit"]["status"] == "FIXED"
    assert issues["2_quantity_unit"]["status"] == "FIXED"
    assert issues["3_market_phase"]["status"] == "PARTIAL_LIVE"
    assert issues["4_simulatable_count"]["status"] == "FIXED"
    assert issues["5_five_live_sessions"]["remaining"] == 2
    assert issues["6_full_session_gap_downtime"]["status"] == "REPORTING_FIXED_FULL_SESSION_PENDING"
    assert issues["7_multi_session_live_replay"]["status"] == "FIXED"
