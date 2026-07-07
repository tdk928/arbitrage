from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from scraper.config import get_settings
from scraper.types import RawFixture


def filter_fixtures(fixtures: list[RawFixture], time_window: str) -> list[RawFixture]:
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    now_utc = datetime.now(tz=ZoneInfo("UTC"))

    if time_window == "next_24h":
        end = now_utc + timedelta(hours=24)
        return [f for f in fixtures if now_utc <= f.kickoff_utc <= end]

    if time_window in ("all", "world_cup"):
        if time_window == "all":
            return fixtures
        wc_start = datetime(2026, 6, 11, tzinfo=timezone.utc)
        wc_end = datetime(2026, 7, 20, 23, 59, 59, tzinfo=timezone.utc)
        return [f for f in fixtures if wc_start <= f.kickoff_utc <= wc_end]

    if time_window == "today_tomorrow":
        today = datetime.now(tz).date()
        tomorrow = today + timedelta(days=1)
        result = []
        for f in fixtures:
            local_date = f.kickoff_utc.astimezone(tz).date()
            if local_date in (today, tomorrow):
                result.append(f)
        return result

    raise ValueError(f"Unknown time_window: {time_window}")
