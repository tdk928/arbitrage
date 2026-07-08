from __future__ import annotations

import pytest

from scraper.v2.arbitrage import compute_arbitrage_v2, display_odd, roi_pct_from_implied


def test_roi_pct_from_implied():
    # 1/1.34 + 1/4.78 ≈ 0.9555 → ~4.66% ROI (France vs Morocco goals 1.5 case)
    implied = 1 / display_odd(1.34) + 1 / display_odd(4.78)
    assert round(roi_pct_from_implied(implied), 2) == pytest.approx(4.66, abs=0.01)


def test_compute_arbitrage_v2_finds_two_bookmaker_arb():
    bookmaker_odds = {
        "betano": [{"role": "over", "name": "Над 1.5", "odd": 1.34}],
        "efbet": [{"role": "under", "name": "Под", "odd": 4.78}],
    }
    result = compute_arbitrage_v2(["over", "under"], bookmaker_odds, min_margin=1.0)
    assert result is not None
    assert result.margin_pct == pytest.approx(4.6601, abs=0.01)
    assert result.bookmaker_count == 2
    assert {leg["bookmaker"] for leg in result.legs} == {"betano", "efbet"}


def test_compute_arbitrage_v2_rejects_single_bookmaker():
    bookmaker_odds = {
        "betano": [
            {"role": "over", "name": "Над", "odd": 2.1},
            {"role": "under", "name": "Под", "odd": 2.0},
        ],
    }
    assert compute_arbitrage_v2(["over", "under"], bookmaker_odds, min_margin=0.0) is None


def test_compute_arbitrage_v2_respects_min_margin():
    bookmaker_odds = {
        "a": [{"role": "over", "name": "Над", "odd": 2.0}],
        "b": [{"role": "under", "name": "Под", "odd": 2.0}],
    }
    # implied = 1.0 → 0% ROI
    assert compute_arbitrage_v2(["over", "under"], bookmaker_odds, min_margin=1.0) is None
    assert compute_arbitrage_v2(["over", "under"], bookmaker_odds, min_margin=0.0) is not None


def test_compute_arbitrage_v2_1x2_three_legs():
    bookmaker_odds = {
        "betano": [{"role": "1", "name": "1", "odd": 1.65}],
        "inbet": [
            {"role": "X", "name": "X", "odd": 4.25},
            {"role": "2", "name": "2", "odd": 6.75},
        ],
    }
    result = compute_arbitrage_v2(["1", "X", "2"], bookmaker_odds, min_margin=1.0)
    assert result is not None
    assert len(result.legs) == 3
    assert result.bookmaker_count == 2
