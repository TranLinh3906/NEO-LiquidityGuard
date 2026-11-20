"""Finite SSI Market Data collector with strict quote-persistence acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any

from data.collector_status import CollectorStatus
from data.market_flags import MarketFlagJoiner
from data.normalize_quotes import normalise_envelope
from data.raw_writer import RawWriter
from .client import SSIReadOnlyClient, jsonable
from .config import SSISettings
from .read_only_guard import assert_ssi_read_only


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _error(exc: Exception) -> str:
    """Return only the exception class so credentials/URLs cannot leak."""
    return type(exc).__name__


def _error_info(exc: Exception) -> dict[str, Any]:
    """Expose only non-secret machine diagnostics from SSI exceptions."""
    info: dict[str, Any] = {"error_type": _error(exc)}
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    if status_code is not None:
        info["http_status"] = status_code
    if code is not None:
        info["provider_code"] = str(code)
    if isinstance(exc, ModuleNotFoundError) and exc.name:
        # A module name is safe operational metadata and is necessary to
        # distinguish a wrong interpreter from an SSI/network failure.
        info["missing_module"] = exc.name
    return info


def _shape(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {"kind": "null", "item_count": 0}
    if isinstance(payload, list):
        return {"kind": "list", "item_count": len(payload)}
    if isinstance(payload, dict):
        return {"kind": "object", "item_count": 1, "field_count": len(payload)}
    return {"kind": type(payload).__name__, "item_count": 1}


def _readback_quotes(root: Path, event_ids: set[str], settings: SSISettings | None = None) -> tuple[int, int, Counter[str]]:
    """Read persisted JSONL back from disk and parse matching QuoteMessages."""
    raw_count = canonical_count = 0
    symbols: Counter[str] = Counter()
    if not event_ids:
        return raw_count, canonical_count, symbols
    for path in sorted((root / "ws").glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                envelope = json.loads(line)
                if envelope.get("raw_event_id") not in event_ids:
                    continue
                raw_count += 1
                records = normalise_envelope(
                    envelope,
                    price_multiplier_to_vnd=settings.quote_price_multiplier_to_vnd if settings else None,
                    quantity_multiplier_to_shares=settings.quote_quantity_multiplier_to_shares if settings else None,
                    unit_evidence_ref=settings.units_evidence_ref if settings else None,
                    complete_book_verified=settings.complete_book_verified if settings else False,
                )
                canonical_count += len(records)
                symbols.update(record["symbol"] for record in records if record.get("symbol"))
    return raw_count, canonical_count, symbols


def run(
    settings: SSISettings, writer: RawWriter, listen_seconds: float, *,
    symbol_rest_preflight: bool = True,
) -> dict[str, Any]:
    symbols = list(settings.symbols)
    status = CollectorStatus()
    missing = settings.missing_credentials()
    if missing:
        status.failed("CONFIG_REQUIRED")
        status.save(settings.status_path)
        return {
            "provider": "SSI", "source": "SSI_FASTCONNECT",
            "status": "CONFIG_REQUIRED", "missing": list(missing),
            "acceptance": {"status": "FAIL", "reason": "MISSING_CREDENTIALS"},
        }

    report: dict[str, Any] = {
        "provider": "SSI", "source": "SSI_FASTCONNECT",
        "checked_at_utc": _now(), "symbols": symbols,
        "collection_scope": settings.collection_scope,
        "symbol_count": len(symbols),
        "configuration": {
            "api_url": settings.api_url,
            "streaming_url": settings.streaming_url,
            "timeout_ms": settings.timeout_ms,
            "max_retries": settings.max_retries,
            "retry_delay_ms": settings.retry_delay_ms,
            "client_rate_cap_rps": settings.max_rps,
            "heartbeat_interval_ms": settings.heartbeat_interval_ms,
            "trusted_ca_bundle": bool(settings.ca_bundle),
            "symbol_rest_preflight": symbol_rest_preflight,
        },
        "rest": {}, "stream": {},
        "unit_verification": {
            "price_multiplier_to_vnd": str(settings.quote_price_multiplier_to_vnd) if settings.quote_price_multiplier_to_vnd is not None else None,
            "quantity_multiplier_to_shares": str(settings.quote_quantity_multiplier_to_shares) if settings.quote_quantity_multiplier_to_shares is not None else None,
            "evidence_ref_present": bool(settings.units_evidence_ref),
            "complete_book_verified": settings.complete_book_verified,
            "price_unit": "VND_PER_SHARE" if settings.quote_price_multiplier_to_vnd is not None and settings.units_evidence_ref else "UNVERIFIED",
            "quantity_unit": "SHARES" if settings.quote_quantity_multiplier_to_shares is not None and settings.units_evidence_ref else "UNVERIFIED",
            "status": "CONFIGURED_WITH_EVIDENCE" if settings.quote_price_multiplier_to_vnd is not None and settings.quote_quantity_multiplier_to_shares is not None and settings.units_evidence_ref else "PENDING_LIVE_SCHEMA_RECONCILIATION",
        },
    }
    client = SSIReadOnlyClient(settings)
    quote_event_ids: set[str] = set()
    counts: Counter[str] = Counter()
    quote_symbols: Counter[str] = Counter()
    market_flag_count = [0]
    market_flags_seen: list[dict[str, str]] = []
    board_map: dict[str, str] = {}
    phase_joiner = MarketFlagJoiner()
    lock = threading.Lock()

    try:
        client.connect()
        report["authentication"] = {"status": "PASS", **client.token_metadata()}

        operations: list[tuple[str, str, str | None, Any]] = []
        if symbol_rest_preflight:
            for symbol in symbols:
                operations.extend((
                    (f"securities_info:{symbol}", "/api/v3/data/securitiesInfo", symbol,
                     lambda symbol=symbol: client.securities_info(symbol)),
                    (f"securities_summary:{symbol}", "/api/v3/data/securitiesSummary", symbol,
                     lambda symbol=symbol: client.securities_summary(symbol)),
                ))
        operations.append(("master_data", "/api/v3/data/masterdata", None, client.master_data))

        for name, endpoint, symbol, operation in operations:
            try:
                payload = jsonable(operation())
                event = writer.write(
                    provider="SSI", source="SSI_FASTCONNECT", mode="LIVE",
                    transport="REST", endpoint_or_channel=endpoint, payload=payload,
                    symbol_hint=symbol, http_status=200,
                )
                shape = _shape(payload)
                report["rest"][name] = {
                    "status": "PASS" if shape["item_count"] else "EMPTY",
                    "raw_event_id": event["raw_event_id"], "schema": shape,
                }
                if name == "master_data" and isinstance(payload, list):
                    board_map = {
                        str(row.get("symbol", "")).upper(): str(row.get("board", "")).upper()
                        for row in payload if isinstance(row, dict) and row.get("symbol") and row.get("board")
                    }
            except Exception as exc:
                report["rest"][name] = {"status": "FAIL", **_error_info(exc)}

        assert_ssi_read_only("stream.quote")
        assert_ssi_read_only("stream.market_flag")
        from ssi_sdk import Stream

        sequence = [0]
        connection_events: list[dict[str, Any]] = []
        acknowledgements: dict[str, str] = {}
        subscriptions_started = [False]

        with Stream(client.auth) as stream:
            ws = stream.streaming

            def persist(message: Any) -> None:
                payload = jsonable(message)
                message_type = type(message).__name__
                # The SDK delivers MarketFlagMessage to both on_data and the
                # typed callback.  Persist it exactly once through on_market_flag.
                if message_type == "MarketFlagMessage":
                    return
                endpoint = {
                    "QuoteMessage": "quote",
                    "MarketFlagMessage": "market.flag",
                }.get(message_type, "ssi_market_data")
                if message_type == "dict" and {"method", "channel", "status"} <= set(payload):
                    endpoint = "stream.control"
                with lock:
                    sequence[0] += 1
                    counts[message_type] += 1
                    event = writer.write(
                        provider="SSI", source="SSI_FASTCONNECT", mode="LIVE",
                        transport="WS", endpoint_or_channel=endpoint, payload=payload,
                        symbol_hint=payload.get("symbol"),
                        provider_timestamp_raw=payload.get("trading_time"),
                        connection_id="ssi-sdk-stream", sequence_no=sequence[0],
                        **(phase_joiner.phase_for(
                            board=board_map.get(str(payload.get("symbol", "")).upper()),
                            quote_time=payload.get("trading_time"),
                        ) if message_type == "QuoteMessage" else {}),
                    )
                    if message_type == "QuoteMessage":
                        quote_event_ids.add(event["raw_event_id"])
                        if payload.get("symbol"):
                            quote_symbols[str(payload["symbol"]).upper()] += 1
                        status.quote_received()
                    else:
                        status.message_received()
                    status.save(settings.status_path)

            def on_market_flag(message: Any) -> None:
                payload = jsonable(message)
                board = str(payload.get("board") or "").upper()
                trading_time = str(payload.get("trading_time") or "")
                flag = str(payload.get("flag") or "").upper()
                received_at = _now()
                accepted = phase_joiner.update(
                    board=board, trading_time=trading_time, flag=flag,
                    received_at_utc=received_at,
                )
                with lock:
                    sequence[0] += 1
                    counts["MarketFlagMessage"] += 1
                    writer.write(
                        provider="SSI", source="SSI_FASTCONNECT", mode="LIVE",
                        transport="WS", endpoint_or_channel="market.flag", payload=payload,
                        provider_timestamp_raw=trading_time,
                        connection_id="ssi-sdk-stream", sequence_no=sequence[0],
                    )
                    market_flag_count[0] += int(accepted)
                    if accepted:
                        market_flags_seen.append({"board": board, "trading_time": trading_time, "flag": flag})
                    status.message_received()
                    status.save(settings.status_path)

            def on_connection(event: Any) -> None:
                payload = jsonable(event)
                state = str(payload.get("state") or "unknown")
                reconnect_count = int(payload.get("reconnect_count") or 0)
                connection_events.append({"state": state, "reconnect_count": reconnect_count})
                if state in {"connected", "reconnected"}:
                    # A reconnect invalidates the previous session flag until
                    # SSI sends a fresh market.flag event.
                    phase_joiner.clear()
                    status.connected("ssi-sdk-stream", symbols, reconnect_count)
                    # The SDK normally restores subscriptions, but explicitly
                    # request them on a reconnect as a defensive integration
                    # guarantee.  Skip the initial connected callback because
                    # subscriptions are issued immediately after ws.connect().
                    if state == "reconnected" and subscriptions_started[0]:
                        # Phase must be subscribed first. Quotes arriving before
                        # a same-board flag remain UNKNOWN and non-simulatable.
                        ws.subscribe_market_flag(on_response=flag_ack)
                        ws.subscribe_symbol_quote(symbols, on_response=quote_ack)
                elif state in {"disconnected", "failed"}:
                    status.failed(f"STREAM_{state.upper()}")
                status.save(settings.status_path)

            def on_heartbeat(_: Any) -> None:
                status.heartbeat()
                status.save(settings.status_path)

            def quote_ack(_: dict[str, Any]) -> None:
                acknowledgements["quote"] = "RECEIVED"

            def flag_ack(_: dict[str, Any]) -> None:
                acknowledgements["market_flag"] = "RECEIVED"

            ws.on_data = persist
            ws.on_market_flag = on_market_flag
            ws.on_connection = on_connection
            ws.on_heartbeat = on_heartbeat
            ws.connect()
            ws.ping(interval_ms=settings.heartbeat_interval_ms)
            # Subscribe phase before quotes so the opening/continuous flag has
            # the earliest possible chance to reach the conservative joiner.
            ws.subscribe_market_flag(on_response=flag_ack)
            ws.subscribe_symbol_quote(symbols, on_response=quote_ack)
            subscriptions_started[0] = True
            subscriptions = ws.list_subscription(timeout_ms=min(settings.timeout_ms, 5_000))
            ws.wait(timeout_ms=listen_seconds * 1000)
            removed = ws.unsubscribe_all()

            report["stream"] = {
                "status": "PASS",
                "subscription_ack": acknowledgements,
                "subscriptions": jsonable(subscriptions),
                "unsubscribed": jsonable(removed),
                "connection_events": connection_events[-10:],
                "reconnect_count": int(getattr(ws, "reconnect_count", 0)),
                "message_count": sum(counts.values()),
                "message_types": dict(counts),
                "quote_count": counts["QuoteMessage"],
                "quote_symbols": dict(quote_symbols),
                "heartbeat_count": status.heartbeat_count,
                "market_flag_count": market_flag_count[0],
                "market_flags_seen": market_flags_seen[-20:],
                "phase_join_status": "VERIFIED" if market_flag_count[0] else "UNKNOWN",
                "board_map_symbols": len(board_map),
            }

        status.stopped()
        status.save(settings.status_path)
    except Exception as exc:
        report.setdefault("authentication", {"status": "FAIL", **_error_info(exc)})
        report["stream"] = {
            "status": "FAIL", **_error_info(exc),
            "message_count": sum(counts.values()), "quote_count": counts["QuoteMessage"],
            "quote_symbols": dict(quote_symbols),
            "market_flag_count": market_flag_count[0],
            "phase_join_status": "VERIFIED" if market_flag_count[0] else "UNKNOWN",
        }
        status.failed(_error(exc))
        status.save(settings.status_path)
    finally:
        client.close()

    raw_count, canonical_count, readback_symbols = _readback_quotes(writer.root, quote_event_ids, settings)
    report["readback"] = {
        "requested_quote_events": len(quote_event_ids),
        "raw_quotes_found": raw_count,
        "canonical_quotes_parsed": canonical_count,
        "symbols": dict(readback_symbols),
    }
    requested = set(symbols)
    observed = set(readback_symbols)
    accepted = bool(quote_event_ids) and raw_count == len(quote_event_ids) and canonical_count > 0 and bool(requested & observed)
    report["acceptance"] = {
        "status": "PASS" if accepted else "FAIL",
        "criterion": "REAL_SSI_QUOTE_PERSISTED_AND_READ_BACK",
        "reason": None if accepted else "NO_READABLE_TARGET_QUOTE",
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and verify real SSI quotes for WATCHLIST, VN30, or ALL scope.")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--report", default="outputs/qa/ssi_live_access_check.json")
    parser.add_argument("--listen-seconds", type=float, default=60.0)
    args = parser.parse_args()
    report = run(SSISettings.from_env(args.env), RawWriter(args.raw_root), args.listen_seconds)
    destination = Path(args.report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("acceptance", {}).get("status") != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
