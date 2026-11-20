"""Refresh the full SSI universe and latest daily trading summaries."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import threading
from data.market_catalog import save_summaries
from data.raw_writer import RawWriter
from .client import SSIReadOnlyClient,jsonable
from .config import SSISettings


def run(settings, *, from_date, to_date, raw_root="data/raw", database="data/processed/market_catalog.sqlite", progress=None):
    if settings.missing_credentials(): return {"status":"CONFIG_REQUIRED"}
    client=SSIReadOnlyClient(settings);writer=RawWriter(raw_root)
    report={"provider":"SSI","from":from_date,"to":to_date,"metadata":{},"summary_rows":0,"symbols":0,"empty_symbols":[],"failed_symbols":{}}
    symbols=set()
    try:
        client.connect()
        try:
            master=jsonable(client.master_data())
            writer.write(transport="REST",endpoint_or_channel="/api/v3/data/masterdata",payload=master,mode="LIVE",http_status=200)
            report["master_data_rows"]=len(master or [])
        except Exception as exc:
            report["master_data_error"]=type(exc).__name__
        equity_symbols=set()
        for board in ("HOSE","HNX","UPCOM"):
            try:
                payload=jsonable(client.securities_by_board(board))
                writer.write(transport="REST",endpoint_or_channel="/api/v3/data/securitiesByBoard",payload={"board":board,"data":payload},mode="LIVE",http_status=200)
                report["metadata"][board]={"status":"PASS","rows":len(payload or [])}
                equity_symbols.update(row["symbol"] for row in payload if row.get("stock_type")=="Stock" and row.get("board")==board)
            except Exception as exc:
                report["metadata"][board]={"status":"FAIL","error_type":type(exc).__name__}
        report["requested_equities"]=len(equity_symbols)
        stopped=threading.Event()
        def fetch(symbol):
            if stopped.is_set(): return symbol,None,"CANCELLED_PERMISSION"
            try:
                return symbol,jsonable(client.market_summary(symbol,from_date,to_date)),None
            except Exception as exc:
                if getattr(exc,"status_code",None) in {401,403}:stopped.set()
                return symbol,None,type(exc).__name__
        # One SDK transport shares its thread-safe provider-aware rate limiter.
        # Writing and SQLite commits stay on this main thread.
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[pool.submit(fetch,symbol) for symbol in sorted(equity_symbols)]
            for completed,future in enumerate(as_completed(futures),1):
                symbol,rows,error=future.result()
                if error: report["failed_symbols"][symbol]=error
                else:
                    event=writer.write(transport="REST",endpoint_or_channel="/api/v3/data/securitiesSummary",payload={"symbol":symbol,"from":from_date,"to":to_date,"data":rows},symbol_hint=symbol,mode="LIVE",http_status=200)
                    if rows:
                        report["summary_rows"]+=save_summaries(rows,database,raw_event_id=event["raw_event_id"]);symbols.add(symbol)
                    else:report["empty_symbols"].append(symbol)
                if progress and (completed%50==0 or completed==len(futures)):
                    progress({"completed":completed,"requested":len(futures),"with_data":len(symbols),"empty":len(report["empty_symbols"]),"failed":len(report["failed_symbols"])})
        report["symbols"]=len(symbols)
        report["status"]="PARTIAL" if report["failed_symbols"] else "PASS" if symbols else "EMPTY"
    except Exception as exc:
        report.update(status="FAIL",error_type=type(exc).__name__,symbols=len(symbols))
    finally:
        client.close()
    return report


def main():
    parser=argparse.ArgumentParser(description="Collect whole-market SSI REST summaries, without subscribing all-market streaming.")
    parser.add_argument("--env",default=".env")
    parser.add_argument("--from-date");parser.add_argument("--to-date")
    parser.add_argument("--report",default="outputs/qa/market_catalog_collect.json")
    args=parser.parse_args();today=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    report=run(SSISettings.from_env(args.env),from_date=args.from_date or (today-timedelta(days=7)).strftime("%Y/%m/%d"),to_date=args.to_date or today.strftime("%Y/%m/%d"),progress=lambda row:print(json.dumps(row),flush=True))
    path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"] not in {"PASS","EMPTY"}: raise SystemExit(2)


if __name__=="__main__":main()
