from __future__ import annotations

from unittest.mock import patch

from scraper.v2 import raw_fetchers
from scraper.v2.raw_fetchers import (
    clear_fetch_caches,
    fetch_all_markets_for_event,
    get_event_fetch_stats,
)
from scraper.v2.types import ParsedMarket, ParsedOutcome

_SAMPLE_MARKETS = [
    ParsedMarket(
        external_id="e1",
        market_name="Над/Под Общо голове 2.5",
        platform="betano",
        bookmaker_slug="betano",
        family="total_goals",
        period="ft",
        scope="match",
        line="2.5",
        outcomes=[
            ParsedOutcome(role="over", name="Над", odd=1.9),
            ParsedOutcome(role="under", name="Под", odd=1.9),
        ],
        specifiers={"type_id": 13},
        provider_template="typeid:13",
    )
]


@patch.object(raw_fetchers, "fetch_raw_payload", return_value={"stub": True})
@patch.object(raw_fetchers, "extract_all_markets", return_value=_SAMPLE_MARKETS)
def test_event_fetch_cache_returns_same_list_and_one_http(mock_extract, mock_payload):
    clear_fetch_caches()

    first = fetch_all_markets_for_event("betano", "betano", "88540009", {})
    second = fetch_all_markets_for_event("betano", "betano", "88540009", {})

    assert first is second
    assert mock_payload.call_count == 1
    assert mock_extract.call_count == 1
    stats = get_event_fetch_stats()
    assert stats["event_fetch_http"] == 1
    assert stats["event_fetch_cache_hits"] == 1


@patch.object(raw_fetchers, "fetch_raw_payload", return_value={"stub": True})
@patch.object(raw_fetchers, "extract_all_markets", return_value=_SAMPLE_MARKETS)
def test_event_fetch_cache_keyed_by_bookmaker_and_event(mock_extract, mock_payload):
    clear_fetch_caches()

    fetch_all_markets_for_event("betano", "betano", "1", {})
    fetch_all_markets_for_event("betano", "betano", "2", {})
    fetch_all_markets_for_event("efbet", "efbet", "1", {})

    assert mock_payload.call_count == 3
    stats = get_event_fetch_stats()
    assert stats["event_fetch_http"] == 3
    assert stats["event_fetch_cache_hits"] == 0


@patch.object(raw_fetchers, "fetch_raw_payload", return_value=None)
def test_empty_payload_cached_so_failed_fetch_not_retried(mock_payload):
    clear_fetch_caches()

    first = fetch_all_markets_for_event("betano", "betano", "missing", {})
    second = fetch_all_markets_for_event("betano", "betano", "missing", {})

    assert first == []
    assert second == []
    assert mock_payload.call_count == 1
    assert get_event_fetch_stats()["event_fetch_cache_hits"] == 1


def test_clear_fetch_caches_resets_stats():
    clear_fetch_caches()
    with patch.object(raw_fetchers, "fetch_raw_payload", return_value={"stub": True}):
        with patch.object(raw_fetchers, "extract_all_markets", return_value=_SAMPLE_MARKETS):
            fetch_all_markets_for_event("betano", "betano", "1", {})
            fetch_all_markets_for_event("betano", "betano", "1", {})
    assert get_event_fetch_stats()["event_fetch_cache_hits"] == 1

    clear_fetch_caches()
    assert get_event_fetch_stats() == {"event_fetch_http": 0, "event_fetch_cache_hits": 0}
