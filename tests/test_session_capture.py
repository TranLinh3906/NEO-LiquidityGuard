from datetime import datetime

import pytest

from ssi_api.session_capture import VN, remaining_window_seconds


def test_morning_duration_runs_to_declared_close_when_started_early():
    now = datetime(2026, 11, 19, 8, 30, tzinfo=VN)
    assert remaining_window_seconds("morning", now) == 3 * 3600


def test_morning_duration_uses_remaining_time_after_open():
    now = datetime(2026, 11, 19, 10, 0, tzinfo=VN)
    assert remaining_window_seconds("morning", now) == 90 * 60


def test_capture_refuses_wrong_window_after_close():
    now = datetime(2026, 11, 19, 11, 31, tzinfo=VN)
    with pytest.raises(ValueError, match="already ended"):
        remaining_window_seconds("morning", now)
