import pytest

from data.deduplicate import DuplicateConflict, DuplicateDetector


def test_only_identical_raw_event_id_is_a_retry_duplicate():
    detector = DuplicateDetector()
    assert not detector.is_retry_duplicate({"raw_event_id": "event-1", "payload_hash": "a", "symbol": "FPT", "received_at_utc": "same-second"})
    assert not detector.is_retry_duplicate({"raw_event_id": "event-2", "payload_hash": "a", "symbol": "FPT", "received_at_utc": "same-second"})
    assert detector.is_retry_duplicate({"raw_event_id": "event-1", "payload_hash": "a"})


def test_event_id_collision_with_different_payload_is_not_silently_dropped():
    detector = DuplicateDetector()
    assert detector.classify({"raw_event_id": "same", "payload_hash": "a"}) == "NEW"
    with pytest.raises(DuplicateConflict):
        detector.classify({"raw_event_id": "same", "payload_hash": "b"})
