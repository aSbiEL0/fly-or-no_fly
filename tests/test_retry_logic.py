from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.weekly_report import _allowed_retry_slots


def test_retry_slots():
    assert _allowed_retry_slots(datetime(2026, 1, 9, 16, tzinfo=ZoneInfo("Europe/London")))
    assert _allowed_retry_slots(datetime(2026, 1, 10, 18, tzinfo=ZoneInfo("Europe/London")))
    assert not _allowed_retry_slots(datetime(2026, 1, 10, 19, tzinfo=ZoneInfo("Europe/London")))
