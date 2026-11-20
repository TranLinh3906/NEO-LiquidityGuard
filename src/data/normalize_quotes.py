"""Convert immutable W2 raw envelopes into W3 canonical quote records."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from typing import Any, Iterator
from uuid import NAMESPACE_URL, uuid5
from decimal import Decimal, InvalidOperation

from .validate_quotes import validate_book

CONTRACT_VERSION = "2.0-draft"


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        pass
    # SSI V3 live QuoteMessage currently uses a timezone-less Vietnam-local
    # form such as 2026/11/16 13:41:47.  The provider contract is Vietnam
    # trading time, so attach UTC+07 rather than treating it as host-local.
    try:
        return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=7)))
    except (TypeError, ValueError):
        return None


def _payloads(envelope: dict[str, Any]) -> Iterator[dict[str, Any]]:
    payload = envelope.get("payload", {})
    if isinstance(payload, dict):
        yield payload


def normalise_envelope(
    envelope: dict[str, Any], *, price_unit: str = "UNVERIFIED",
    quantity_unit: str = "UNVERIFIED", allowed_phases: set[str] | None = None,
    stale_after_seconds: float | None = None,
    price_multiplier_to_vnd: Decimal | str | int | float | None = None,
    quantity_multiplier_to_shares: Decimal | str | int | float | None = None,
    unit_evidence_ref: str | None = None,
    complete_book_verified: bool = False,
) -> list[dict[str, Any]]:
    """Normalise an SSI QuoteMessage without inventing missing book levels."""
    transport = envelope.get("transport")
    if transport not in {"REST", "WS"}:
        raise ValueError("raw envelope must have REST or WS transport")
    records = []
    for payload_index, payload in enumerate(_payloads(envelope)):
        is_ssi_quote = envelope.get("endpoint_or_channel") == "quote" and payload.get("type") == "quote"
        if not is_ssi_quote:
            continue
        symbol = str(payload.get("symbol") or envelope.get("symbol_hint") or "").strip().upper() or None
        phase = envelope.get("market_phase") or payload.get("market_phase")
        phase_source = envelope.get("market_phase_source") or ("PAYLOAD" if payload.get("market_phase") else "UNKNOWN")
        phase_board = envelope.get("market_phase_board")
        phase_received_at = envelope.get("market_phase_received_at")
        array_fields = ("bid_prices", "bid_volumes", "ask_prices", "ask_volumes")
        lengths = {
            field: len(payload[field]) if isinstance(payload.get(field), list) else 0
            for field in array_fields
        }
        ssi_arrays_complete = all(length >= 3 for length in lengths.values())
        completeness = "COMPLETE" if ssi_arrays_complete else "UNKNOWN"
        update_type = "FULL_BOOK" if ssi_arrays_complete else "PARTIAL_BOOK"
        provider_time = envelope.get("provider_timestamp_raw") or payload.get("trading_time")
        mode = str(envelope.get("mode") or "SYNTHETIC_TEST").upper()
        initial_flags: list[str] = [] if provider_time else ["MISSING_PROVIDER_TIME"]
        if mode not in {"LIVE", "REPLAY", "SYNTHETIC_TEST"}:
            initial_flags.append("INVALID_MODE_LABEL")
            mode = "SYNTHETIC_TEST"
        provider = envelope.get("provider", "SSI")
        source = envelope.get("source", "SSI_FASTCONNECT")
        if provider != "SSI":
            initial_flags.append("UNEXPECTED_PROVIDER")
        if source != "SSI_FASTCONNECT":
            initial_flags.append("UNEXPECTED_SOURCE")
        received_time = _parse_time(envelope.get("received_at_utc"))
        parsed_provider_time = _parse_time(provider_time)
        arrival_delay_seconds = None
        is_stale = False
        if received_time and parsed_provider_time and received_time.utcoffset() is not None and parsed_provider_time.utcoffset() is not None:
            arrival_delay_seconds = (received_time - parsed_provider_time).total_seconds()
            if stale_after_seconds is not None and arrival_delay_seconds > stale_after_seconds:
                initial_flags.append("STALE")
                is_stale = True
        def multiplier(value: Decimal | str | int | float | None) -> Decimal | None:
            if value is None:
                return None
            try:
                parsed = Decimal(str(value))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError("unit multipliers must be numeric") from exc
            if parsed <= 0:
                raise ValueError("unit multipliers must be positive")
            return parsed

        price_multiplier = multiplier(price_multiplier_to_vnd)
        quantity_multiplier = multiplier(quantity_multiplier_to_shares)
        multiplier_evidence_ok = not (price_multiplier is not None or quantity_multiplier is not None) or bool(unit_evidence_ref)
        effective_price_unit = price_unit
        effective_quantity_unit = quantity_unit
        if price_multiplier is not None and effective_price_unit == "UNVERIFIED" and multiplier_evidence_ok:
            effective_price_unit = "VND_PER_SHARE"
        if quantity_multiplier is not None and effective_quantity_unit == "UNVERIFIED" and multiplier_evidence_ok:
            effective_quantity_unit = "SHARES"
        if not multiplier_evidence_ok:
            initial_flags.append("MISSING_UNIT_EVIDENCE")
        quote: dict[str, Any] = {
            "schema_version": CONTRACT_VERSION,
            "quote_id": str(uuid5(NAMESPACE_URL, f"ssi-quote:{envelope['raw_event_id']}:{payload_index}:{symbol or ''}")),
            "raw_event_id": envelope["raw_event_id"],
            "symbol": symbol, "source_type": transport,
            "source": source, "source_mode": mode, "provider": provider,
            "received_at_utc": envelope["received_at_utc"], "quote_time_vn": provider_time,
            "time_source": "PROVIDER" if provider_time else "UNKNOWN",
            "market_phase": phase, "market_phase_raw": phase, "market_phase_source": phase_source,
            "market_phase_board": phase_board, "market_phase_received_at": phase_received_at,
            "snapshot_completeness": completeness,
            "update_type": update_type, "partial_update_policy": "PRESERVE_NO_MERGE",
            "book_level_count": min(lengths.values()), "array_lengths": lengths,
            "is_complete_snapshot": completeness == "COMPLETE", "is_stale": is_stale,
            "arrival_delay_seconds": arrival_delay_seconds,
            "connection_id": envelope.get("connection_id"), "sequence_no": envelope.get("sequence_no"),
            "endpoint_or_channel": envelope.get("endpoint_or_channel"),
            "quality_flags": initial_flags, "normalization_version": CONTRACT_VERSION,
            "price_unit": effective_price_unit, "quantity_unit": effective_quantity_unit,
            "price_multiplier_to_vnd": str(price_multiplier) if price_multiplier is not None else None,
            "quantity_multiplier_to_shares": str(quantity_multiplier) if quantity_multiplier is not None else None,
            "unit_evidence_ref": unit_evidence_ref, "complete_book_verified": bool(complete_book_verified),
            "payload_hash": envelope.get("payload_hash"),
        }
        for side in ("bid", "ask"):
            for level in range(1, 4):
                prices = payload.get(f"{side}_prices") or []
                volumes = payload.get(f"{side}_volumes") or []
                raw_price = deepcopy(prices[level - 1]) if len(prices) >= level else None
                raw_qty = deepcopy(volumes[level - 1]) if len(volumes) >= level else None
                quote[f"raw_{side}_price_{level}"] = raw_price
                quote[f"raw_{side}_qty_{level}"] = raw_qty
                quote[f"{side}_price_{level}"] = (str(Decimal(str(raw_price)) * price_multiplier) if raw_price is not None and price_multiplier is not None else raw_price)
                quote[f"{side}_qty_{level}"] = (str(Decimal(str(raw_qty)) * quantity_multiplier) if raw_qty is not None and quantity_multiplier is not None else raw_qty)
        units_verified = effective_price_unit != "UNVERIFIED" and effective_quantity_unit != "UNVERIFIED" and multiplier_evidence_ok
        records.append(validate_book(quote, units_verified=units_verified, allowed_phases=allowed_phases))
    return records
