"""LiquidityGuard seven-page workspace; run with streamlit run this file."""
from __future__ import annotations
import time
from app import components, pages, state
from app.styles import inject
from app.universe import load_universe, restrict_to_latest_capture
from app.view_models import ROOT, assess, is_observable_book, load_quotes, local_time, make_view, read_status, parse_time


def workspace(st,ss,universe,context,execution_layout=False):
    # Native fragment controls rerun this workspace. Refresh the outer header
    # and filters only when a navigation/global preference transition needs it.
    current=(ss["page"],ss["mode"],ss["selected_symbol"],ss["density"],ss["number_format"])
    if current!=context or "pending_preferences" in ss:
        st.rerun(scope="app")
    components.NUMBER_FORMAT.set(ss["number_format"])
    status=read_status()
    rows=load_quotes(ss["mode"],ss["selected_symbol"])
    dates=sorted({parse_time(r.get("quote_time_vn") or r.get("received_at_utc")).date().isoformat() for r in rows if parse_time(r.get("quote_time_vn") or r.get("received_at_utc"))})
    if ss["mode"]=="LIVE" and dates:
        rows=[r for r in rows if parse_time(r.get("quote_time_vn") or r.get("received_at_utc")).date().isoformat()==dates[-1]]
    if ss["mode"]=="REPLAY" or ss["page"]=="Replay":
        if dates:
            if ss["selected_date"] not in dates: ss["selected_date"]=dates[-1]
            if not execution_layout:
                st.selectbox("Ngày có dữ liệu",dates,key="selected_date",on_change=lambda:ss.update(snapshot_id=None,playing=False))
            rows=[r for r in rows if parse_time(r.get("quote_time_vn") or r.get("received_at_utc")).date().isoformat()==ss["selected_date"]]
    if execution_layout and ss.get("selected_session") != "Cả ngày":
        morning = ss["selected_session"] == "Phiên sáng"
        rows = [
            row for row in rows
            if (lambda stamp: stamp is not None and ((stamp.hour < 12) if morning else (stamp.hour >= 12)))(
                parse_time(row.get("quote_time_vn") or row.get("received_at_utc"))
            )
        ]
    ids=[r["quote_id"] for r in rows]
    if ss["snapshot_id"] not in ids or (ss["mode"]=="LIVE" and not ss.get("simulation_record")):
        # LIVE must follow the newest event even when it is blocked. REPLAY,
        # however, should open on the newest eligible stored snapshot so a
        # user is not greeted by empty charts merely because the final event
        # of the day arrived after a reconnect without a fresh market.flag.
        eligible = [row for row in rows if assess(row,"REPLAY",status)["allowed"]]
        observable = [row for row in rows if is_observable_book(row)]
        replay_default = eligible[-1] if eligible else observable[-1] if observable else None
        ss["snapshot_id"]=(replay_default["quote_id"] if ss["mode"]=="REPLAY" and replay_default else ids[-1] if ids else None)
    if ss["page"]=="Replay" and len(rows)>1:
        if ss["playing"] and time.monotonic()-ss.get("last_replay_tick",0)>=.8:
            ss["last_replay_tick"]=time.monotonic()
            nxt=min(len(ids)-1,ids.index(ss["snapshot_id"])+ss["replay_speed"])
            ss["snapshot_id"]=ids[nxt]
            if nxt==len(ids)-1: ss["playing"]=False
        ss["snapshot_picker"]=ss["snapshot_id"]
        st.select_slider("Timeline · snapshot",options=ids,key="snapshot_picker",format_func=lambda value:local_time(next(r for r in rows if r["quote_id"]==value).get("quote_time_vn"),True),on_change=lambda:ss.update(snapshot_id=ss["snapshot_picker"]))
    quote=next((r for r in rows if r["quote_id"]==ss["snapshot_id"]),None)
    vm=make_view(quote,ss["mode"],status,ss["trade_side"],ss["requested_qty"],stale_seconds=ss["stale_seconds"])
    if execution_layout:
        pages.simulator(st,ss,vm,rows,status,universe)
        return
    compact_label=" · COMPACT SSI REPLAY" if (quote or {}).get("replay_bundle")=="COMPACT_SSI_REPLAY" else ""
    badge="SYNTHETIC_TEST · Dữ liệu giả lập để thử công thức và giao diện" if ss["mode"]=="SYNTHETIC_TEST" else f"{ss['mode']} · {vm['trust']['label']}{compact_label} · SSI FastConnect · WS {status.get('state','offline').upper()}"
    if ss["page"]=="Market Pulse":badge=f"THỊ TRƯỜNG · SSI REST thực đã lưu · Chế độ mô phỏng L3: {ss['mode']}"
    st.markdown(f'<div class="lg-mode-banner">◉ {badge} · {ss["selected_symbol"]}</div>',unsafe_allow_html=True)
    if ss["page"] not in {"Dashboard","Simulator"}: components.mode_control(st,ss)
    main_col,right=st.columns([3.25,1],gap="small")
    with main_col:
        page=ss["page"]
        if page=="Dashboard": pages.dashboard(st,ss,vm,rows,status)
        elif page=="Market Pulse": pages.market_pulse(st,ss,vm,rows,status,universe)
        elif page=="Simulator": pages.simulator(st,ss,vm,rows,status,universe)
        elif page=="Replay": pages.replay(st,ss,vm,rows,status)
        elif page=="Charts": pages.chart_studio(st,ss,vm,rows,status)
        elif page=="Alerts": pages.alerts(st,ss,vm,rows,status)
        elif page=="Settings": pages.settings(st,ss,status)
    with right: components.right_rail(st,ss,vm,rows,status,universe)
    st.markdown('<div class="lg-footer">LiquidityGuard · Gen Z Liquidity Intelligence · Mô phỏng giả định trong ba mức giá · Chỉ đọc dữ liệu thị trường</div>',unsafe_allow_html=True)


def main():
    import streamlit as st
    st.set_page_config(page_title="LiquidityGuard · Liquidity Intelligence",page_icon="🦝",layout="wide",initial_sidebar_state="collapsed")
    ss=st.session_state; state.init(ss)
    if ss.get("mode") not in {"LIVE","REPLAY"}:
        state.change_mode(ss,"REPLAY")
    if not ss.get("view_applied"):
        requested=st.query_params.get("view","")
        if requested=="market":ss["page"]="Market Pulse"
        if requested=="simulator":ss["page"]="Simulator"
        ss["view_applied"]=True
    if "pending_preferences" in ss: ss.update(ss.pop("pending_preferences"))
    components.NUMBER_FORMAT.set(ss["number_format"])
    inject(st,ss["density"])
    @st.cache_data(show_spinner=False)
    def cached_universe(signature):
        full = load_universe(ROOT/"data/raw/rest",ROOT/"data/universe/sector_overrides.csv")
        return restrict_to_latest_capture(full, ROOT/"outputs/qa")
    source_paths=list((ROOT/"data/raw/rest").glob("*.jsonl"))+list((ROOT/"outputs/qa").glob("ssi_capture_*.json"))
    signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in source_paths)
    universe=cached_universe(signature)
    if not universe:
        st.error("Không tìm thấy báo cáo capture SSI hợp lệ; Dashboard không mở rộng sang catalog chưa thu.")
        st.stop()
    context=(ss["page"],ss["mode"],ss["selected_symbol"],ss["density"],ss["number_format"])
    interval="1s" if ss["page"]=="Replay" else "5s" if ss["mode"]=="LIVE" else None
    if ss["page"]=="Simulator":
        with st.container(key="lg_exec_shell"):
            sidebar,body=st.columns([236,1436],gap="small")
            with sidebar: components.execution_sidebar(st,ss)
            with body:
                components.execution_topbar(st,ss,universe)
                st.markdown('<div class="lg-execution-lab"></div>',unsafe_allow_html=True)
                st.fragment(run_every=interval)(workspace)(st,ss,universe,context,True)
    else:
        components.header(st,ss); components.controls(st,ss,universe)
        rail,content=st.columns([.55,12],gap="small")
        with rail: components.navrail(st,ss)
        with content:
            st.fragment(run_every=interval)(workspace)(st,ss,universe,context)


if __name__=="__main__": main()
