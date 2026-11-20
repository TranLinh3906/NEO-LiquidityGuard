"""Duplicate classification that never collapses updates by symbol and second."""
from __future__ import annotations


class DuplicateConflict(ValueError):
    """The same raw_event_id appeared with a different payload hash."""


class DuplicateDetector:
    def __init__(self) -> None:
        self._events: dict[str, str | None] = {}

    def classify(self, envelope: dict) -> str:
        event_id = envelope["raw_event_id"]
        payload_hash = envelope.get("payload_hash")
        if event_id not in self._events:
            self._events[event_id] = payload_hash
            return "NEW"
        if self._events[event_id] != payload_hash:
            raise DuplicateConflict(f"raw_event_id collision: {event_id}")
        return "RETRY_DUPLICATE"

    def is_retry_duplicate(self, envelope: dict) -> bool:
        """Only an already-seen immutable raw event ID is safe to discard automatically."""
        return self.classify(envelope) == "RETRY_DUPLICATE"
