"""Idempotent raw-to-canonical processing entry points."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterator
from .deduplicate import DuplicateDetector
from .normalize_quotes import normalise_envelope
from .quote_store import QuoteStore


def raw_envelopes(paths: list[str | Path]) -> Iterator[dict]:
    for path in paths:
        with Path(path).open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip(): yield json.loads(line)


def process(
    paths: list[str | Path], store: QuoteStore, *, price_unit: str = "UNVERIFIED",
    quantity_unit: str = "UNVERIFIED", allowed_phases: set[str] | None = None,
    stale_after_seconds: float | None = None, price_multiplier_to_vnd=None,
    quantity_multiplier_to_shares=None, unit_evidence_ref: str | None = None,
    complete_book_verified: bool = False, replace_existing: bool = False,
) -> dict[str, int]:
    detector, counts = DuplicateDetector(), {
        "raw_events": 0, "retry_duplicates": 0, "non_quote_events_skipped": 0,
        "quote_records": 0, "full_book_records": 0, "partial_book_records": 0,
        "quotes_inserted": 0, "quotes_updated": 0, "quotes_existing": 0,
    }
    for envelope in raw_envelopes(paths):
        counts["raw_events"] += 1
        if detector.is_retry_duplicate(envelope):
            counts["retry_duplicates"] += 1
            continue
        quotes = normalise_envelope(
            envelope, price_unit=price_unit, quantity_unit=quantity_unit,
            allowed_phases=allowed_phases, stale_after_seconds=stale_after_seconds,
            price_multiplier_to_vnd=price_multiplier_to_vnd,
            quantity_multiplier_to_shares=quantity_multiplier_to_shares,
            unit_evidence_ref=unit_evidence_ref, complete_book_verified=complete_book_verified,
        )
        if not quotes:
            counts["non_quote_events_skipped"] += 1
        for quote in quotes:
            counts["quote_records"] += 1
            key = "full_book_records" if quote.get("update_type") == "FULL_BOOK" else "partial_book_records"
            counts[key] += 1
            inserted = store.insert(quote, commit=False)
            counts["quotes_inserted"] += int(inserted)
            if not inserted and replace_existing:
                counts["quotes_updated"] += int(store.update(quote, commit=False))
            else:
                counts["quotes_existing"] += int(not inserted)
    store.commit()
    return counts


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Process immutable provider raw JSONL files into canonical SQLite quotes.")
    parser.add_argument("inputs", nargs="+", help="Raw JSONL file(s), never a credential file")
    parser.add_argument("--database", default="data/processed/quotes.sqlite")
    parser.add_argument("--price-unit", default="UNVERIFIED", help="Use a concrete verified unit, e.g. VND_PER_SHARE")
    parser.add_argument("--quantity-unit", default="UNVERIFIED", help="Use a concrete verified unit, e.g. SHARES")
    parser.add_argument("--allowed-phase", action="append", default=[], help="Repeat for each verified simulatable phase")
    parser.add_argument("--stale-after-seconds", type=float, default=None, help="Flag late arrivals using provider vs receive time")
    parser.add_argument("--price-multiplier", default=None, help="Verified SSI quote price multiplier to VND/share")
    parser.add_argument("--quantity-multiplier", default=None, help="Verified SSI quote quantity multiplier to shares")
    parser.add_argument("--unit-evidence-ref", default=None, help="Document or ticket proving the unit convention")
    parser.add_argument("--complete-book-verified", action="store_true", help="Only set after SSI confirms the quote is a complete snapshot")
    parser.add_argument("--replace-existing", action="store_true", help="Re-normalise an existing quote from the same immutable raw event")
    args = parser.parse_args()
    store = QuoteStore(args.database)
    try:
        print(process(
            args.inputs, store, price_unit=args.price_unit,
            quantity_unit=args.quantity_unit, allowed_phases=set(args.allowed_phase) or None,
            stale_after_seconds=args.stale_after_seconds,
            price_multiplier_to_vnd=args.price_multiplier, quantity_multiplier_to_shares=args.quantity_multiplier,
            unit_evidence_ref=args.unit_evidence_ref, complete_book_verified=args.complete_book_verified,
            replace_existing=args.replace_existing,
        ))
    finally:
        store.close()


if __name__ == "__main__":
    main()
