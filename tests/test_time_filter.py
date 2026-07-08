from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from scraper.time_filter import filter_fixtures
from scraper.types import RawFixture


def _fixture(hours_from_now: float, slug: str = "efbet") -> RawFixture:
    return RawFixture(
        home_team="A",
        away_team="B",
        kickoff_utc=datetime.now(tz=timezone.utc) + timedelta(hours=hours_from_now),
        external_id="1",
        bookmaker_slug=slug,
    )


def test_next_24h_includes_upcoming_excludes_past_and_far_future():
    fixtures = [
        _fixture(-1),
        _fixture(2),
        _fixture(23),
        _fixture(25),
    ]
    result = filter_fixtures(fixtures, "next_24h")
    assert len(result) == 2
    assert all(0 <= (f.kickoff_utc - datetime.now(tz=timezone.utc)).total_seconds() <= 86400 for f in result)


def test_world_cup_window():
    inside = RawFixture(
        home_team="A",
        away_team="B",
        kickoff_utc=datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc),
        external_id="1",
        bookmaker_slug="efbet",
    )
    outside = RawFixture(
        home_team="C",
        away_team="D",
        kickoff_utc=datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
        external_id="2",
        bookmaker_slug="efbet",
    )
    result = filter_fixtures([inside, outside], "world_cup")
    assert result == [inside]


def test_unknown_time_window_raises():
    with pytest.raises(ValueError, match="Unknown time_window"):
        filter_fixtures([], "invalid")
