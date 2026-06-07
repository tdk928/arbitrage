from __future__ import annotations

from datetime import datetime, timedelta
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

    if time_window == "all":
        return fixtures

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
