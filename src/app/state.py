"""One workspace state shared by all seven Streamlit pages."""
from ssi_api.symbol_groups import VN30_SYMBOLS
PAGES = ["Dashboard", "Market Pulse", "Simulator", "Replay", "Charts", "So sánh mã", "Alerts", "Settings"]
ICONS = ["house", "activity", "play", "history", "chart-no-axes-column-increasing", "layers", "bell", "settings"]
_WATCHLIST_PRIORITY = ("FPT", "VPB", "SSI", "HPG", "VNM", "VCB", "MWG", "TCB", "MBB", "VIC")
DEFAULT_WATCHLIST = list(dict.fromkeys(_WATCHLIST_PRIORITY + VN30_SYMBOLS))
DEFAULTS = {
    "page": "Dashboard", "mode": "REPLAY", "selected_symbol": "FPT",
    "trade_side": "BUY", "requested_qty": 400, "snapshot_id": None,
    "selected_date": None, "playing": False, "replay_speed": 1,
    "selected_session": "Cả ngày",
    "density": "Thoải mái", "number_format": "1.234,56", "watchlist": DEFAULT_WATCHLIST,
    "compare_symbols": ["FPT", "VPB", "SSI", "HPG", "VNM"],
    "stale_seconds": 60, "compare_snapshot_id": None, "compare_open": False,
}


def init(state):
    from copy import deepcopy
    for key, value in DEFAULTS.items():
        state.setdefault(key, deepcopy(value))


def navigate(state, page):
    state["page"] = page
    if page == "Replay" and state["mode"] == "LIVE":
        change_mode(state,"REPLAY")
    if page != "Replay":
        state["playing"] = False


def select_symbol(state, symbol):
    state["selected_symbol"] = symbol
    state["w_symbol"] = symbol
    state["snapshot_id"] = None
    state["selected_date"] = None
    state["playing"] = False
    state.pop("simulation_record", None)


def change_mode(state, mode):
    state["mode"] = mode
    state["w_mode"] = mode
    state["snapshot_id"] = None
    state["selected_date"] = None
    state["playing"] = False
    state.pop("simulation_record", None)


def change_session(state, session):
    state["selected_session"] = session
    state["snapshot_id"] = None
    state["playing"] = False
    state.pop("simulation_record", None)
