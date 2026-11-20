"""FinTech interactive workspace for the SSI LiquidityGuard dashboard."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

from data.pipeline import process
from data.ohlc_history import intraday_liquidity_windows, load_bars, summarize
from data.quote_store import QuoteStore
from finance.execution import simulate_sweep
from finance.explain import explain
from finance.liquidity import liquidity_metrics

try:
    from .universe import BOARD_LABELS, load_universe, universe_summary
except ImportError:  # Streamlit executes this file as a top-level script.
    from app.universe import BOARD_LABELS, load_universe, universe_summary


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT / "data/processed/quotes.sqlite"
SAMPLE_PATH = ROOT / "data_sample/synthetic_ssi_quote_envelope.jsonl"
STATUS_PATH = ROOT / "data/runtime/collector_status.json"
OHLC_PATH = ROOT / "data/processed/ohlc_history.jsonl"
NAV = ["Tổng quan", "Execution Lab", "Time Machine", "Cảnh báo", "Data Trust"]


def _sample_store() -> QuoteStore:
    store = QuoteStore(":memory:")
    process([SAMPLE_PATH], store, price_unit="VND_PER_SHARE", quantity_unit="SHARES", allowed_phases={"LO"})
    return store


def load_quotes(mode: str, symbol: str, database: str | Path = DEFAULT_DATABASE) -> tuple[list[dict[str, Any]], str]:
    mode = mode.upper()
    if mode == "SYNTHETIC_TEST":
        store = _sample_store()
        try:
            rows = list(store.records(symbol=symbol or None, provider="SSI", source="SSI_FASTCONNECT"))
        finally:
            store.close()
        return rows, "SYNTHETIC_TEST — fixture SSI, không phải dữ liệu thị trường thật"
    store = QuoteStore(database)
    try:
        rows = list(store.records(symbol=symbol or None, original_mode="LIVE"))
    finally:
        store.close()
    if mode == "REPLAY":
        return [{**row, "source_mode": "REPLAY", "original_source_mode": row.get("source_mode")} for row in rows], "REPLAY — dữ liệu SSI đã lưu, chỉ đọc"
    return rows, "LIVE — canonical SSI đã lưu; không gọi lệnh giao dịch"


def load_ohlc(symbol: str, timeframe: str, path: str | Path = OHLC_PATH) -> list[dict[str, Any]]:
    return load_bars(path, symbol=symbol, timeframe=timeframe)


def status_snapshot(path: str | Path = STATUS_PATH) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "UNKNOWN", "provider": "SSI", "source": "SSI_FASTCONNECT"}


def book_rows(quote: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "level": level,
        "bid_price": quote.get(f"bid_price_{level}"),
        "bid_qty": quote.get(f"bid_qty_{level}"),
        "ask_price": quote.get(f"ask_price_{level}"),
        "ask_qty": quote.get(f"ask_qty_{level}"),
    } for level in range(1, 4)]


def _num(value: Any) -> float | None:
    try:
        return float(Decimal(str(value))) if value is not None and value != "" else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def observed_book(quote: dict[str, Any]) -> dict[str, Any]:
    """Structural observations for charts; eligibility still gates W4 metrics."""
    bids = [_num(quote.get(f"bid_qty_{i}")) or 0 for i in range(1, 4)]
    asks = [_num(quote.get(f"ask_qty_{i}")) or 0 for i in range(1, 4)]
    bid_prices = [_num(quote.get(f"bid_price_{i}")) for i in range(1, 4)]
    ask_prices = [_num(quote.get(f"ask_price_{i}")) for i in range(1, 4)]
    bid_depth, ask_depth = sum(bids), sum(asks)
    best_bid, best_ask = bid_prices[0], ask_prices[0]
    spread = best_ask - best_bid if best_bid is not None and best_ask is not None else None
    mid = (best_ask + best_bid) / 2 if best_bid is not None and best_ask is not None else None
    return {
        "bid_qty": bids, "ask_qty": asks, "bid_prices": bid_prices, "ask_prices": ask_prices,
        "bid_depth": bid_depth, "ask_depth": ask_depth,
        "obi": (bid_depth - ask_depth) / (bid_depth + ask_depth) if bid_depth + ask_depth else None,
        "spread": spread, "mid": mid,
        "spread_bps": spread / mid * 10_000 if spread is not None and mid else None,
    }


def _history_observations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in sorted(rows, key=lambda item: (item.get("received_at_utc") or "", item.get("quote_id") or "")):
        item = observed_book(row)
        item.update({"time": row.get("quote_time_vn") or row.get("received_at_utc"), "quote_id": row.get("quote_id"), "source_mode": row.get("source_mode")})
        output.append(item)
    return output


def _chart(st, data: list[dict[str, Any]], mark: str, title: str, x: str, y: str, color: str | None = None, *, height: int = 250) -> None:
    import altair as alt
    if not data:
        st.info("Chưa đủ snapshot để vẽ biểu đồ này.")
        return
    chart = alt.Chart(alt.Data(values=data)).mark_bar() if mark == "bar" else alt.Chart(alt.Data(values=data)).mark_line(point=True)
    enc = chart.encode(x=alt.X(f"{x}:N", title=None), y=alt.Y(f"{y}:Q", title=None), tooltip=list(data[0].keys()))
    if color:
        enc = enc.encode(color=alt.Color(f"{color}:N", title=None))
    st.altair_chart(enc.properties(title=title, height=height), use_container_width=True)


def _coverage_curve(quote: dict[str, Any], side: str, maximum: int) -> list[dict[str, Any]]:
    if not quote.get("is_simulatable"):
        return []
    sizes = sorted({max(1, int(maximum * fraction)) for fraction in (0.25, 0.5, 0.75, 1, 1.25, 1.5)})
    return [{"requested": size, "coverage": float(simulate_sweep(quote, side, size)["coverage_ratio"] * 100)} for size in sizes]


def _impact_curve(quote: dict[str, Any], side: str, maximum: int) -> list[dict[str, Any]]:
    if not quote.get("is_simulatable"):
        return []
    sizes = sorted({max(1, int(maximum * fraction)) for fraction in (0.25, 0.5, 0.75, 1, 1.25)})
    data = []
    for size in sizes:
        result = simulate_sweep(quote, side, size)
        if result["vwap_filled"] is not None:
            data.append({"requested": size, "vwap": float(result["vwap_filled"]), "slippage_bps": float(result["slippage_bps"] or 0)})
    return data


def _risk_alerts(quote: dict[str, Any] | None, simulation: dict[str, Any] | None, status: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    if not quote:
        return [{"severity": "HIGH", "title": "Không có snapshot", "detail": "Chưa có quote đã lưu cho mã và chế độ đã chọn."}]
    if simulation and simulation.get("unfilled_qty"):
        alerts.append({"severity": "MEDIUM", "title": "Khối lượng vượt ba mức", "detail": f"Còn thiếu {simulation['unfilled_qty']:,} CP; không ngoại suy level 4."})
    flags = quote.get("quality_flags", [])
    if flags:
        alerts.append({"severity": "HIGH", "title": "Data Trust đang chặn mô phỏng", "detail": ", ".join(flags)})
    if quote.get("is_stale"):
        alerts.append({"severity": "HIGH", "title": "Snapshot cũ", "detail": "Quote bị gắn STALE; không dùng cho LIVE simulation."})
    if status.get("state") != "online" and quote.get("source_mode") == "LIVE":
        alerts.append({"severity": "MEDIUM", "title": "Collector offline", "detail": f"Trạng thái hiện tại: {status.get('state', 'unknown')}"})
    if not alerts:
        alerts.append({"severity": "LOW", "title": "Không có cảnh báo cấu trúc", "detail": "Snapshot vượt qua các kiểm tra hiện có."})
    return alerts


def _css(st) -> None:
    st.markdown("""
    <style>
      :root {
        --deep-plum: #3E2F4F; --dusty-lavender: #BDAFD1; --soft-lilac: #DCCFF0;
        --warm-sand: #D7B38C; --cream-beige: #F2E6D7; --blush-pink: #F3C9DD;
        --primary: #9563C4; --background: #FAF7FC; --text-primary: #30243C;
        --bid: #A8DDB5; --ask: #F2A0B6; --accent-orange: #F4BF91;
      }
      .stApp { background: var(--background); color: var(--text-primary); }
      [data-testid="stHeader"] { background: var(--background); }
      .block-container { padding-top: 1rem; max-width: 1540px; }
      [data-testid="stSidebar"] { background: linear-gradient(180deg, var(--deep-plum), #574267); }
      [data-testid="stSidebar"] * { color: #fffaff !important; }
      [data-testid="stSidebar"] .stCaption { color: #eadff4 !important; }
      div[data-testid="stMetric"] { background: linear-gradient(145deg, #fffaff, var(--cream-beige)); border: 1px solid var(--dusty-lavender); border-radius: 18px; padding: 12px 14px; box-shadow: 0 5px 18px #3e2f4f18; }
      div[data-testid="stMetricLabel"] { color: #715b82; }
      div[data-testid="stMetricValue"] { color: var(--text-primary); }
      .lg-topbar { background: linear-gradient(115deg, var(--deep-plum), #5b416d 60%, #75517d); color: #fffaff; border-radius: 22px; padding: 18px 24px; box-shadow: 0 12px 30px #3e2f4f35; margin-bottom: 14px; }
      .lg-brand { font-size: 1.45rem; font-weight: 850; letter-spacing: -0.02em; }
      .lg-brand-mark { display: inline-flex; width: 38px; height: 38px; align-items: center; justify-content: center; border-radius: 13px; background: linear-gradient(145deg, var(--blush-pink), var(--warm-sand)); color: var(--deep-plum); margin-right: 9px; }
      .lg-topbar-meta { color: #eadff4; font-size: .86rem; margin-top: 4px; }
      .lg-status-pill { display: inline-block; border: 1px solid #eadff477; border-radius: 999px; padding: 7px 12px; margin: 3px 4px 0 0; font-size: .78rem; color: #fffaff; }
      .lg-card { background: #fffaff; border: 1px solid var(--dusty-lavender); border-radius: 20px; padding: 18px; margin-bottom: 14px; box-shadow: 0 5px 18px #3e2f4f14; }
      .lg-panel { background: linear-gradient(145deg, #fffaff, #f4edf9); border: 1px solid var(--soft-lilac); border-radius: 20px; padding: 18px; }
      .lg-risk { border-left: 6px solid #d95b72; background: #fff0f4; padding: 12px 16px; border-radius: 12px; margin: 8px 0; }
      .lg-warn { border-left: 6px solid var(--accent-orange); background: #fff6ed; padding: 12px 16px; border-radius: 12px; margin: 8px 0; }
      .lg-ok { border-left: 6px solid #83bf8f; background: #effaf0; padding: 12px 16px; border-radius: 12px; margin: 8px 0; }
      .lg-title { color: var(--deep-plum); font-size: 2.15rem; font-weight: 850; letter-spacing: -0.04em; }
      .lg-subtitle { color: #715b82; margin-top: -10px; }
      .lg-section-title { color: var(--deep-plum); font-size: 1.15rem; font-weight: 800; }
      .lg-mini { color: #715b82; font-size: .82rem; }
      .stButton > button { border-radius: 999px; border: 1px solid var(--dusty-lavender); background: #fffaff; color: var(--deep-plum); font-weight: 700; }
      .stButton > button:hover { border-color: var(--primary); color: var(--primary); }
      div[data-baseweb="select"] > div, input, textarea { border-radius: 12px !important; border-color: var(--dusty-lavender) !important; background: #fffaff !important; }
      .stRadio [role="radiogroup"] { gap: 8px; }
      .stRadio label { background: #fffaff; border: 1px solid var(--soft-lilac); border-radius: 999px; padding: 4px 10px; }
      [data-testid="stExpander"] { border-color: var(--soft-lilac); border-radius: 16px; background: #fffaff; }
    </style>
    """, unsafe_allow_html=True)


def _controls(st, universe: list[dict[str, Any]], *, compact: bool = False) -> tuple[str, str, str, str, int, str]:
    grid = st.columns([1.05, 1.25, 1.15, 1.05, 1.15, 1.2]) if compact else [st] * 6
    target = grid
    boards = ["ALL"] + sorted({row["board"] for row in universe})
    board = target[0].selectbox("Thị trường", boards, format_func=lambda value: "Tất cả thị trường" if value == "ALL" else BOARD_LABELS.get(value, value), key="lg_board")
    board_rows = [row for row in universe if board == "ALL" or row["board"] == board]
    sectors = ["ALL"] + sorted({row["sector"] for row in board_rows})
    sector = target[1].selectbox("Nhóm ngành", sectors, format_func=lambda value: "Tất cả ngành" if value == "ALL" else ("Chưa phân loại" if value == "UNCLASSIFIED" else value), key="lg_sector")
    filtered = [row for row in board_rows if sector == "ALL" or row["sector"] == sector]
    search = target[2].text_input("Tìm mã", value="", placeholder="FPT / VPB / HPG", key="lg_search").strip().upper()
    if search:
        filtered = [row for row in filtered if search in row["symbol"]]
    symbols = [row["symbol"] for row in filtered] or ["VPB"]
    symbol = target[3].selectbox("Mã cổ phiếu", symbols, key="lg_symbol")
    mode = target[4].selectbox("Chế độ dữ liệu", ["LIVE", "REPLAY", "SYNTHETIC_TEST"], key="lg_mode")
    side = target[5].radio("Chiều giao dịch", ["BUY", "SELL"], horizontal=True, key="lg_side") if compact else st.radio("Chiều giao dịch", ["BUY", "SELL"], horizontal=True, key="lg_side")
    quantity = int(st.number_input("Khối lượng giả định (CP)", min_value=1, value=4200, step=100, key="lg_quantity"))
    return board, sector, symbol, mode, quantity, side


def _header(st, status: dict[str, Any], mode: str, universe: list[dict[str, Any]]) -> None:
    summary = universe_summary(universe)
    st.markdown(f'''<div class="lg-topbar"><div class="lg-brand"><span class="lg-brand-mark">🦝</span>LiquidityGuard <span style="color:#F3C9DD">/ Risk Radar</span></div><div class="lg-topbar-meta">Quan sát thanh khoản · mô phỏng khối lượng · đánh giá kết quả · kiểm chứng dữ liệu</div><div style="margin-top:10px"><span class="lg-status-pill">◉ {mode}</span><span class="lg-status-pill">SSI FastConnect · read-only</span><span class="lg-status-pill">Collector: {str(status.get("state", "UNKNOWN")).upper()}</span><span class="lg-status-pill">Universe: {summary['symbols']:,} mã</span></div></div>''', unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("Data status", mode)
    cols[1].metric("Provider", "SSI FastConnect")
    cols[2].metric("Collector", str(status.get("state", "UNKNOWN")).upper())
    cols[3].metric("Universe", f"{summary['symbols']:,} mã")
    cols[4].metric("Quote mới nhất", status.get("last_quote_at_utc") or "—")
    st.caption(f"A · Danh mục: {summary['symbols']:,} mã · B · LIVE watchlist: cấu hình SSI_SYMBOLS · C · Toàn thị trường: khóa mặc định cho tới khi SSI cấp quyền/kiểm chứng hiệu năng")


def _quick_rail(st, quote, history, status) -> None:
    """Right-hand workspace rail inspired by the supplied FinTech mockup."""
    st.markdown('<div class="lg-panel"><div class="lg-section-title">⚡ Quick Tasks</div>', unsafe_allow_html=True)
    if st.button("▶  Mô phỏng giao dịch mới", key="quick_simulate", use_container_width=True):
        st.session_state["lg_nav"] = "Execution Lab"; st.rerun()
    if st.button("↻  Replay phiên", key="quick_replay", use_container_width=True):
        st.session_state["lg_nav"] = "Time Machine"; st.rerun()
    if st.button("▱  So sánh thanh khoản", key="quick_compare", use_container_width=True):
        st.session_state["lg_nav"] = "Tổng quan"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="lg-panel"><div class="lg-section-title">☆ Watchlist</div><div class="lg-mini">VPB · FPT · SSI</div>', unsafe_allow_html=True)
    for symbol in ("VPB", "FPT", "SSI"):
        st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #dccff055"><span>☆ <b>{symbol}</b></span><span class="lg-mini">SSI quote</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    latest = history[-1] if history else {}
    spread_text = f"{latest.get('spread_bps'):.2f} bps" if latest.get("spread_bps") is not None else "—"
    obi_text = f"{latest.get('obi'):.3f}" if latest.get("obi") is not None else "—"
    st.markdown(f'<div class="lg-panel"><div class="lg-section-title">▣ Session Snapshot</div><div class="lg-mini">Cập nhật: {status.get("last_quote_at_utc") or "—"}</div><hr><div>Spread <b>{spread_text}</b></div><div>OBI <b>{obi_text}</b></div><div>Snapshot <b>{quote.get("source_mode") if quote else "—"}</b></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="lg-panel"><div class="lg-section-title">🎨 Brand Palette</div><div style="display:flex;gap:6px;margin-top:10px"><span style="width:28px;height:28px;border-radius:8px;background:#3E2F4F"></span><span style="width:28px;height:28px;border-radius:8px;background:#BDAFD1"></span><span style="width:28px;height:28px;border-radius:8px;background:#DCCFF0"></span><span style="width:28px;height:28px;border-radius:8px;background:#D7B38C"></span><span style="width:28px;height:28px;border-radius:8px;background:#F3C9DD"></span></div><div class="lg-mini">Deep Plum · Dusty Lavender · Soft Lilac · Warm Sand · Blush Pink</div></div>', unsafe_allow_html=True)


def _render_overview(st, quote, history, simulation, mode, quantity, side, status) -> None:
    if not quote:
        st.warning("Chưa có snapshot cho lựa chọn này. Hãy đổi mã/chế độ hoặc chạy collector SSI.")
        return
    observed = observed_book(quote)
    metrics = liquidity_metrics(quote)
    kpi = st.columns(5)
    kpi[0].metric("Spread", f"{observed['spread']:.2f}" if observed["spread"] is not None else "—")
    kpi[1].metric("Spread bps", f"{observed['spread_bps']:.2f}" if observed["spread_bps"] is not None else "—")
    kpi[2].metric("Bid depth 3", f"{observed['bid_depth']:,.0f}")
    kpi[3].metric("Ask depth 3", f"{observed['ask_depth']:,.0f}")
    kpi[4].metric("OBI 3", f"{observed['obi']:.4f}" if observed["obi"] is not None else "—")
    st.caption(f"Snapshot ID: `{quote.get('quote_id')}` · quote time: {quote.get('quote_time_vn') or '—'} · {mode}")
    if not metrics["is_eligible"]:
        st.warning("KPI trên là quan sát cấu trúc của book; W4 financial simulation vẫn bị khóa bởi Data Trust.")
    left, right = st.columns(2)
    with left:
        _chart(st, [{"side": "Bid", "share": observed["bid_depth"] / (observed["bid_depth"] + observed["ask_depth"]) * 100 if observed["bid_depth"] + observed["ask_depth"] else 0}, {"side": "Ask", "share": observed["ask_depth"] / (observed["bid_depth"] + observed["ask_depth"]) * 100 if observed["bid_depth"] + observed["ask_depth"] else 0}], "bar", "1. Bid/Ask Balance · tỷ trọng thanh khoản chờ", "side", "share", height=220)
        cumulative = []
        bid, ask = 0, 0
        for level, row in enumerate(book_rows(quote), 1):
            bid += row["bid_qty"] or 0; ask += row["ask_qty"] or 0
            cumulative.extend(({"level": f"L{level}", "side": "Bid", "cumulative": bid}, {"level": f"L{level}", "side": "Ask", "cumulative": ask}))
        _chart(st, cumulative, "line", "2. Cumulative Order Book · độ sâu tích lũy", "level", "cumulative", "side", height=250)
    with right:
        _chart(st, [{"level": f"L{i}", "side": "Bid", "quantity": observed["bid_qty"][i-1]} for i in range(1, 4)] + [{"level": f"L{i}", "side": "Ask", "quantity": observed["ask_qty"][i-1]} for i in range(1, 4)], "bar", "Độ sâu mirror ba mức", "level", "quantity", "side", height=220)
        timeline = _history_observations(history)
        _chart(st, [{"time": row["time"], "side": side, "depth": row["bid_depth"] if side == "BUY" else row["ask_depth"]} for row in timeline] + [{"time": row["time"], "side": "OTHER", "depth": row["ask_depth"] if side == "BUY" else row["bid_depth"]} for row in timeline], "line", "8. Bid/Ask Depth Timeline", "time", "depth", "side", height=250)
    st.subheader("6. OBI Timeline · quan sát mất cân bằng")
    _chart(st, [{"time": row["time"], "obi": row["obi"]} for row in _history_observations(history) if row["obi"] is not None], "line", "OBI theo snapshot", "time", "obi", height=240)
    st.subheader("7. Spread Timeline · biến động spread")
    _chart(st, [{"time": row["time"], "spread": row["spread"]} for row in _history_observations(history) if row["spread"] is not None], "line", "Spread theo snapshot", "time", "spread", height=240)
    st.subheader("Historical OHLCV · Giá, khối lượng và giá trị giao dịch")
    daily = load_ohlc(quote.get("symbol", ""), "1d")
    minute = load_ohlc(quote.get("symbol", ""), "1m")
    if daily:
        stats = summarize(daily)[0]
        st.caption(f"{stats['first_date']} → {stats['last_date']} · {stats['bar_count']:,} phiên · dữ liệu OHLCV lịch sử, không phải L3 order book")
        _chart(st, [{"date": row.get("trading_date"), "close": _num(row.get("close")) or 0} for row in daily[-500:]], "line", "Giá đóng cửa theo thời gian", "date", "close", height=240)
        _chart(st, [{"date": row.get("trading_date"), "volume": _num(row.get("volume")) or 0, "value": _num(row.get("value")) or 0} for row in daily[-500:]], "line", "Khối lượng và giá trị giao dịch", "date", "value", height=240)
    else:
        st.info("Chưa có OHLCV lịch sử cho mã này. Chạy ssi_api.ohlc_collect để bổ sung dữ liệu.")
    if minute:
        windows = intraday_liquidity_windows(minute)
        st.caption("Phân tích nội ngày 1 phút: các khung 30 phút được xếp theo giá trị giao dịch.")
        _chart(st, windows[:24], "bar", "Thanh khoản nội ngày theo khung giờ", "time_bucket", "value", "symbol", height=240)


def _render_execution(st, quote, simulation, side, quantity) -> None:
    st.subheader("Execution Lab · mô phỏng từ một snapshot cố định")
    if not quote:
        st.warning("Chưa có snapshot để mô phỏng."); return
    st.caption(f"Snapshot cố định: `{quote.get('quote_id')}` · {side} {quantity:,} CP")
    cols = st.columns(5)
    cols[0].metric("Đã đáp ứng", f"{simulation['filled_qty']:,}")
    cols[1].metric("Chưa đáp ứng", f"{simulation['unfilled_qty']:,}")
    cols[2].metric("Coverage", f"{simulation['coverage_ratio'] * 100:.2f}%")
    cols[3].metric("VWAP", str(simulation.get("vwap_filled") or "—"))
    cols[4].metric("Slippage bps", f"{simulation['slippage_bps']:.2f}" if simulation.get("slippage_bps") is not None else "—")
    allocations = [{"level": f"L{fill['level']}", "filled": fill["filled_qty"], "available": fill["available_qty"]} for fill in simulation.get("level_fills", [])]
    _chart(st, allocations, "bar", "3. Sweep Allocation · phân bổ vào từng mức", "level", "filled", height=240)
    book_side = "bid" if side == "SELL" else "ask"
    max_qty = max(quantity, int(sum((quote.get(f"{book_side}_qty_{i}") or 0) for i in range(1, 4))))
    left, right = st.columns(2)
    with left:
        _chart(st, _coverage_curve(quote, side, max_qty), "line", "4. Coverage Curve", "requested", "coverage", height=240)
    with right:
        _chart(st, _impact_curve(quote, side, max_qty), "line", "5. VWAP Price Impact · bps", "requested", "slippage_bps", height=240)
    if simulation.get("warnings"):
        st.warning("; ".join(simulation["warnings"]) + ". Không ngoại suy giá ngoài ba mức.")
    if not simulation.get("is_simulatable"):
        st.error(simulation.get("rejection_reason") or "Data Trust đang chặn mô phỏng LIVE.")
    st.info(explain(liquidity_metrics(quote), simulation))
    st.dataframe(allocations, width="stretch", hide_index=True)


def _render_replay(st, rows, selected_index: int) -> None:
    st.subheader("Time Machine · Replay theo snapshot")
    if not rows:
        st.info("Chưa có replay cho mã này."); return
    st.caption("Chọn một snapshot để giữ nguyên depth và simulator; không trộn dữ liệu giữa các thời điểm.")
    row = rows[selected_index]
    st.json({"snapshot_id": row.get("quote_id"), "source_mode": row.get("source_mode"), "original_source_mode": row.get("original_source_mode"), "quote_time_vn": row.get("quote_time_vn"), "received_at_utc": row.get("received_at_utc")})
    timeline = _history_observations(rows)
    _chart(st, [{"time": item["time"], "metric": "Spread", "value": item["spread"]} for item in timeline if item["spread"] is not None] + [{"time": item["time"], "metric": "OBI", "value": item["obi"]} for item in timeline if item["obi"] is not None], "line", "Liquidity Timeline · replay", "time", "value", "metric", height=300)


def _render_alerts(st, quote, simulation, status) -> None:
    st.subheader("Risk Radar · cảnh báo và hành động")
    for alert in _risk_alerts(quote, simulation, status):
        cls = "lg-risk" if alert["severity"] == "HIGH" else "lg-warn" if alert["severity"] == "MEDIUM" else "lg-ok"
        st.markdown(f'<div class="{cls}"><b>{alert["title"]}</b><br>{alert["detail"]}</div>', unsafe_allow_html=True)
    if st.button("Mở Execution Lab với snapshot này", key="open_execution_from_risk"):
        st.session_state["lg_nav"] = "Execution Lab"
        st.rerun()


def _render_trust(st, quote, mode, universe_row) -> None:
    st.subheader("Data Trust · kiểm chứng nguồn")
    values = {
        "Provider": quote.get("provider") if quote else "—",
        "Source": quote.get("source") if quote else "—",
        "Mode": mode,
        "Snapshot ID": quote.get("quote_id") if quote else "—",
        "Raw event ID": quote.get("raw_event_id") if quote else "—",
        "Board": universe_row.get("board_label") if universe_row else "—",
        "Sector": universe_row.get("sector") if universe_row else "—",
        "Price unit": quote.get("price_unit") if quote else "—",
        "Quantity unit": quote.get("quantity_unit") if quote else "—",
        "Market phase": quote.get("market_phase") if quote else "—",
        "Quality flags": ", ".join(quote.get("quality_flags", [])) if quote else "NO_QUOTE",
    }
    st.dataframe([{"field": key, "value": value} for key, value in values.items()], width="stretch", hide_index=True)
    if quote and (quote.get("price_unit") == "UNVERIFIED" or quote.get("quantity_unit") == "UNVERIFIED" or not quote.get("market_phase")):
        st.error("LIVE financial simulation bị khóa: cần xác minh đơn vị và market phase. Không được dùng fixture để thay thế.")
    else:
        st.success("Data Trust đủ điều kiện cho các kiểm tra hiện có.")


def _render() -> None:
    import streamlit as st

    st.set_page_config(page_title="LiquidityGuard — Risk Radar", page_icon="🔥", layout="wide")
    _css(st)
    universe = load_universe(ROOT / "data/raw/rest", ROOT / "data/universe/sector_overrides.csv")
    status = status_snapshot()
    with st.sidebar:
        st.markdown("### 🦝 LiquidityGuard")
        st.caption("SSI FastConnect · read-only workspace")
        st.markdown("---")
        st.caption("Các trang dùng chung mã, chiều giao dịch, khối lượng và snapshot.")
        st.divider()
        st.caption("Không phát sinh lệnh thật.")
    _header(st, status, st.session_state.get("lg_mode", "LIVE"), universe)
    st.markdown('<div class="lg-card"><div class="lg-section-title">Global Control Bar</div><div class="lg-mini">Mã CP · thị trường · nhóm ngành · LIVE/REPLAY/DEMO · chiều giao dịch · khối lượng</div>', unsafe_allow_html=True)
    board, sector, symbol, mode, quantity, side = _controls(st, universe, compact=True)
    st.markdown('</div>', unsafe_allow_html=True)
    nav = st.radio("Navigation", NAV, horizontal=True, key="lg_nav", label_visibility="collapsed")
    rows, note = load_quotes(mode, symbol)
    if mode == "SYNTHETIC_TEST" and symbol != "SSI":
        st.info("Fixture hiện chỉ có mã SSI; universe production vẫn hiển thị toàn bộ mã từ SSI masterdata.")
    universe_row = next((row for row in universe if row["symbol"] == symbol), None)
    if rows:
        rows = sorted(rows, key=lambda row: (row.get("received_at_utc") or "", row.get("quote_id") or ""))
        selected_index = len(rows) - 1
        if nav in {"Time Machine", "Execution Lab", "Cảnh báo", "Data Trust"}:
            selected_index = st.slider("Snapshot", 0, len(rows) - 1, len(rows) - 1, key="lg_snapshot")
        selected = rows[selected_index]
    else:
        selected_index, selected = 0, None
    locked = st.session_state.get("lg_locked_snapshot")
    current_ids = {row.get("quote_id") for row in rows}
    if locked and locked.get("quote_id") not in current_ids:
        st.session_state.pop("lg_locked_snapshot", None)
        locked = None
    if st.button("🔒 Khóa snapshot & tính", key="lg_lock_snapshot", disabled=selected is None):
        st.session_state["lg_locked_snapshot"] = dict(selected) if selected else None
        locked = st.session_state.get("lg_locked_snapshot")
    quote = locked if locked else selected
    simulation = simulate_sweep(quote, side, quantity) if quote else None
    if locked:
        st.success(f"Snapshot đang khóa: `{locked.get('quote_id')}`. Dữ liệu WebSocket mới không trộn vào lần tính này.")
    st.info(note)
    if nav == "Tổng quan":
        main_col, rail_col = st.columns([3.8, 1.15])
        with main_col:
            _render_overview(st, quote, rows, simulation, mode, quantity, side, status)
        with rail_col:
            _quick_rail(st, quote, _history_observations(rows), status)
    elif nav == "Execution Lab":
        _render_execution(st, quote, simulation, side, quantity)
    elif nav == "Time Machine":
        _render_replay(st, rows, selected_index)
    elif nav == "Cảnh báo":
        _render_alerts(st, quote, simulation, status)
    else:
        _render_trust(st, quote, mode, universe_row)


def main() -> None:
    _render()


if __name__ == "__main__":
    main()
