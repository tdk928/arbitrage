from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.arbitrage_v3 import get_db, router
from api.routes.auth import require_subscribed_client_or_admin
from scraper.models_auth import Role, User
from scraper.models_v3 import ArbitrageAudit
from scraper.v3.arbitrage import (
    AUDIT_LIMIT,
    OpportunityV3,
    build_event_key,
    merge_top10_into_audit,
)

app = FastAPI()
app.include_router(router)


def _subscribed_client() -> User:
    now = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    role = Role(id=1, slug="client", name="Client")
    return User(
        id=2,
        email="client@example.com",
        password_hash="hashed",
        role_id=role.id,
        registered_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
        active_from=now - timedelta(hours=1),
        active_to=now + timedelta(hours=23),
        role=role,
    )


def _override_subscribed_client():
    app.dependency_overrides[require_subscribed_client_or_admin] = lambda: _subscribed_client()


def _opp(
  *,
  home: str = "France",
  away: str = "Morocco",
  rule_slug: str = "total_goals_ou",
  line: str = "1.5",
  margin_pct: float = 4.5,
) -> OpportunityV3:
    return OpportunityV3(
        rule_set_id=1,
        rule_slug=rule_slug,
        line=line,
        margin_pct=margin_pct,
        implied_total=0.95,
        legs=[],
        bookmaker_count=2,
        home_team=home,
        away_team=away,
        kickoff_utc=datetime(2026, 7, 10, 18, 0, tzinfo=timezone.utc),
        market_label=f"Market {line}",
    )


def test_build_event_key_distinguishes_markets_on_same_match():
    ou = _opp(rule_slug="total_goals_ou", line="1.5")
    btts = _opp(rule_slug="both_teams_to_score", line="")
    assert build_event_key(ou) != build_event_key(btts)


def test_build_event_key_is_stable_for_team_name_order():
    a = _opp(home="France", away="Morocco")
    b = _opp(home="Morocco", away="France")
    assert build_event_key(a) == build_event_key(b)


def test_merge_top10_into_audit_keeps_highest_margin_for_same_event():
    session = MagicMock()
    existing = ArbitrageAudit(
        id=1,
        event_key=build_event_key(_opp(margin_pct=3.0)),
        margin_pct=3.0,
        scrape_run_id=1,
        captured_at=datetime(2026, 7, 8, 8, 0, tzinfo=timezone.utc),
        rule_slug="total_goals_ou",
        implied_total=0.97,
        bookmaker_count=2,
        home_team="France",
        away_team="Morocco",
        market_label="Market 1.5",
        legs=[],
    )
    query = session.query.return_value
    filter_by = query.filter_by
    filter_by.return_value.one_or_none.return_value = existing

    captured_at = datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc)
    merge_top10_into_audit(session, 2, [_opp(margin_pct=5.0)], captured_at)

    assert float(existing.margin_pct) == 5.0
    assert existing.scrape_run_id == 2
    assert existing.captured_at == captured_at
    session.add.assert_not_called()


def test_merge_top10_into_audit_does_not_downgrade_existing_event():
    session = MagicMock()
    existing = ArbitrageAudit(
        id=1,
        event_key=build_event_key(_opp(margin_pct=6.0)),
        margin_pct=6.0,
        scrape_run_id=1,
        captured_at=datetime(2026, 7, 8, 8, 0, tzinfo=timezone.utc),
        rule_slug="total_goals_ou",
        implied_total=0.94,
        bookmaker_count=2,
        home_team="France",
        away_team="Morocco",
        market_label="Market 1.5",
        legs=[],
    )
    session.query.return_value.filter_by.return_value.one_or_none.return_value = existing

    merge_top10_into_audit(
        session,
        2,
        [_opp(margin_pct=4.0)],
        datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc),
    )

    assert float(existing.margin_pct) == 6.0
    assert existing.scrape_run_id == 1


def test_merge_top10_into_audit_trims_to_audit_limit():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.one_or_none.return_value = None

    rows = [
        ArbitrageAudit(
            id=i,
            event_key=f"event-{i}",
            margin_pct=float(100 - i),
            scrape_run_id=1,
            captured_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
            rule_slug="total_goals_ou",
            implied_total=0.9,
            bookmaker_count=2,
            home_team=f"Home {i}",
            away_team=f"Away {i}",
            market_label="Market",
            legs=[],
        )
        for i in range(1, AUDIT_LIMIT + 6)
    ]
    session.query.return_value.order_by.return_value.all.return_value = rows

    merge_top10_into_audit(
        session,
        1,
        [_opp(home="Spain", away="Brazil", margin_pct=1.0)],
        datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc),
    )

    deleted_ids = [call.args[0].id for call in session.delete.call_args_list]
    assert deleted_ids == list(range(AUDIT_LIMIT + 1, AUDIT_LIMIT + 6))


def test_get_audit_returns_empty_list_when_no_rows():
    session = MagicMock()
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    _override_subscribed_client()
    try:
        response = TestClient(app).get(
            "/arbitrage/v3/audit",
            headers={"Authorization": "Bearer client-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_get_audit_returns_rows_ordered_by_margin():
    row = ArbitrageAudit(
        id=3,
        scrape_run_id=6,
        captured_at=datetime(2026, 7, 8, 9, 30, 15, tzinfo=timezone.utc),
        event_key="france|morocco|2026-07-10T18:00:00+00:00|total_goals_ou|1.5",
        rule_set_id=1,
        rule_slug="total_goals_ou",
        line="1.5",
        margin_pct=4.66,
        implied_total=0.9555,
        bookmaker_count=2,
        home_team="France",
        away_team="Morocco",
        kickoff_utc=datetime(2026, 7, 10, 18, 0, tzinfo=timezone.utc),
        market_label="Over/Under Total Goals (match) 1.5",
        legs=[{"role": "over", "bookmaker": "betano", "odd": 1.34}],
    )
    session = MagicMock()
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [row]

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    _override_subscribed_client()
    try:
        response = TestClient(app).get(
            "/arbitrage/v3/audit",
            headers={"Authorization": "Bearer client-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rank"] == 1
    assert data[0]["event_key"] == "france|morocco|2026-07-10T18:00:00+00:00|total_goals_ou|1.5"
    assert data[0]["margin_pct"] == 4.66
    assert data[0]["scrape_date"] == "2026-07-08"
    assert data[0]["scrape_time"] == "09:30:15"


def test_get_audit_returns_rows_ordered_by_roi():
    captured_at = datetime(2026, 7, 8, 9, 30, 15, tzinfo=timezone.utc)
    common = {
        "scrape_run_id": 6,
        "captured_at": captured_at,
        "rule_set_id": 1,
        "rule_slug": "total_goals_ou",
        "line": "1.5",
        "implied_total": 0.9555,
        "bookmaker_count": 2,
        "kickoff_utc": datetime(2026, 7, 10, 18, 0, tzinfo=timezone.utc),
        "market_label": "Over/Under Total Goals (match) 1.5",
        "legs": [],
    }
    row_high = ArbitrageAudit(
        id=2,
        event_key="spain|brazil|2026-07-10T18:00:00+00:00|total_goals_ou|1.5",
        margin_pct=8.0,
        home_team="Spain",
        away_team="Brazil",
        **common,
    )
    row_low = ArbitrageAudit(
        id=1,
        event_key="france|morocco|2026-07-10T18:00:00+00:00|total_goals_ou|1.5",
        margin_pct=3.0,
        home_team="France",
        away_team="Morocco",
        **common,
    )
    session = MagicMock()
    session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
        row_high,
        row_low,
    ]

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    _override_subscribed_client()
    try:
        response = TestClient(app).get(
            "/arbitrage/v3/audit",
            headers={"Authorization": "Bearer client-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert [row["margin_pct"] for row in data] == [8.0, 3.0]
    assert [row["rank"] for row in data] == [1, 2]
