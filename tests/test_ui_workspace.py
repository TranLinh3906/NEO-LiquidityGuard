"""UI integration and financial honesty tests using clearly synthetic fixtures."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from app.state import PAGES, init, select_symbol, change_mode
from app.view_models import (
    assess,
    coverage_points,
    is_observable_book,
    make_view,
    observation_history_points,
    resolve_quote_database,
    synthetic_quotes,
)


def test_ui_does_not_release_unknown_ssi_book_or_offline_live():
    quote=synthetic_quotes("FPT")[-1]
    # Deliberately simulate a real canonical row while keeping known gates missing.
    quote.update(source_mode="LIVE",unit_evidence_ref=None,market_phase_source=None,complete_book_verified=False)
    view=make_view(quote,"LIVE",{"state":"offline"},"BUY",400)
    assert not view["trust"]["allowed"]
    assert view["metrics"]=={} and view["simulation"] is None
    assert view["trust"]["label"]=="OFFLINE"
    assert len(view["trust"]["reasons"])>=4


def test_verified_but_stale_online_quote_remains_blocked():
    quote=synthetic_quotes("FPT")[-1]
    quote.update(source_mode="LIVE",market_phase_source="SSI_MARKET_FLAG",unit_evidence_ref="SSI-DOC",complete_book_verified=True)
    now=datetime(2026,11,18,tzinfo=timezone.utc)
    gate=assess(quote,"LIVE",{"state":"online","updated_at_utc":now.isoformat()},now=now)
    assert not gate["allowed"]
    assert any("STALE" in reason for reason in gate["reasons"])


def test_phase_unknown_book_is_observable_but_not_simulatable():
    quote = synthetic_quotes("FPT")[-1]
    quote.update(
        source_mode="REPLAY",
        market_phase=None,
        market_phase_source="UNKNOWN",
    )

    assert is_observable_book(quote)
    assert not assess(quote, "REPLAY", {"state": "offline"})["allowed"]
    points = observation_history_points([quote])
    assert len(points) == 1
    assert points[0]["snapshot_id"] == quote["quote_id"]


def test_incomplete_three_level_book_is_not_observable():
    quote = synthetic_quotes("FPT")[-1]
    quote["ask_price_3"] = None
    assert not is_observable_book(quote)
    assert observation_history_points([quote]) == []


def test_ssi_zero_zero_empty_level_remains_observable_only():
    quote = synthetic_quotes("FPT")[-1]
    quote.update(
        source_mode="REPLAY",
        market_phase=None,
        market_phase_source="UNKNOWN",
        ask_price_3=None,
        ask_qty_3=0,
    )
    assert is_observable_book(quote)
    assert len(observation_history_points([quote])) == 1
    assert not assess(quote, "REPLAY", {"state": "offline"})["allowed"]


def test_verified_one_sided_snapshot_can_render_depth_but_not_spread():
    quote = synthetic_quotes("FPT")[-1]
    quote.update(
        source_mode="REPLAY",
        market_phase=None,
        market_phase_source="UNKNOWN",
        bid_price_1=None,
        bid_price_2=None,
        bid_price_3=None,
        bid_qty_1=0,
        bid_qty_2=0,
        bid_qty_3=0,
    )
    assert is_observable_book(quote)
    point = observation_history_points([quote])[0]
    assert point["spread_bps"] is None
    assert point["bid_depth_3"] == 0
    assert point["obi_3"] == -1
    assert not assess(quote, "REPLAY", {"state": "offline"})["allowed"]


def test_ui_350_share_book_returns_87_5_without_mutating_snapshot():
    quote=synthetic_quotes("SSI")[-1]
    quote.update(ask_qty_1=100,ask_qty_2=100,ask_qty_3=150)
    before=deepcopy(quote)
    view=make_view(quote,"SYNTHETIC_TEST",{"state":"offline"},"BUY",400)
    assert view["simulation"]["coverage_ratio"]==Decimal(".875")
    assert view["simulation"]["unfilled_qty"]==50
    assert all(fill["level"]<=3 for fill in view["simulation"]["level_fills"])
    assert quote==before
    coverage=coverage_points(quote,"BUY",500)
    assert all(a["coverage"]>=b["coverage"] for a,b in zip(coverage,coverage[1:]))


def test_symbol_and_mode_transitions_discard_incompatible_snapshot():
    state={}; init(state)
    state.update(snapshot_id="old",simulation_record={"quote":{}},playing=True)
    select_symbol(state,"SSI")
    assert state["snapshot_id"] is None and not state["playing"]
    assert "simulation_record" not in state
    change_mode(state,"REPLAY")
    assert state["mode"]==state["w_mode"]=="REPLAY"


def test_synthetic_execution_lab_supports_any_captured_symbol_and_chart_invariants():
    from app import charts
    quote = synthetic_quotes("HPG")[-1]
    view = make_view(quote,"SYNTHETIC_TEST",{"state":"offline"},"BUY",10_000)
    assert view["trust"]["allowed"]
    simulation = view["simulation"]
    assert sum(charts.sweep(simulation).data[0].values) == simulation["requested_qty"]
    assert all(fill["level"] <= 3 for fill in simulation["level_fills"])
    coverage = coverage_points(quote,"BUY",10_000)
    assert all(a["coverage"] >= b["coverage"] for a,b in zip(coverage,coverage[1:]))


def test_all_seven_pages_preserve_shared_state_and_live_blocks_simulator():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/"src/app/dashboard.py").run(timeout=45)
    assert not app.exception
    assert app.session_state["mode"]=="REPLAY"
    assert "SYNTHETIC_TEST" not in str(app.button_group)
    # The real local replay store can exceed one million quote rows; allow
    # enough time for the symbol switch in full-suite CI without weakening
    # the state and navigation assertions below.
    app.button(key="watch_VPB").click().run(timeout=60)
    selected_id=app.session_state["snapshot_id"]
    for page in PAGES:
        # Rendering chart-heavy pages can exceed 30 seconds when the full
        # suite is sharing CPU; keep this browser-style integration check
        # deterministic without weakening its assertions.
        app.button(key="nav_"+page).click().run(timeout=60)
        assert not app.exception, page
        assert app.session_state["selected_symbol"]=="VPB"
        assert app.session_state["requested_qty"]==400
        assert app.session_state["snapshot_id"]==selected_id
    app.button(key="nav_Dashboard").click().run(timeout=60)
    # AppTest exposes segmented controls as button_group.
    app.session_state["mode"]="LIVE";app.session_state["w_mode"]="LIVE"
    app.run(timeout=60)
    assert app.button(key="run_simulation").disabled
    assert not app.exception


def test_observable_replay_book_is_not_hidden_when_simulation_gate_is_blocked():
    quote = synthetic_quotes("FPT")[-1]
    quote.update(source_mode="REPLAY", market_phase=None, market_phase_source="UNKNOWN")
    assert is_observable_book(quote)
    view = make_view(quote, "REPLAY", {"state": "offline"}, "BUY", 400)
    assert not view["trust"]["allowed"]
    assert view["simulation"] is None


def test_replay_uses_compact_cloud_bundle_only_when_primary_store_is_missing(tmp_path, monkeypatch):
    import app.view_models as view_models

    monkeypatch.setattr(view_models, "ROOT", tmp_path)
    compact = tmp_path / "data_sample/ssi_compact_replay.sqlite"
    compact.parent.mkdir(parents=True)
    compact.touch()

    assert resolve_quote_database("REPLAY") == compact
    assert resolve_quote_database("LIVE") == tmp_path / "data/processed/quotes.sqlite"
