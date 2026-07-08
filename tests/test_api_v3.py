from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.arbitrage_v3 import get_db, router

app = FastAPI()
app.include_router(router)

from scraper.models_v3 import ArbitrageTop10Current


@pytest.fixture
def client():
    return TestClient(app)


def test_get_top10_returns_empty_list_when_no_rows():
    session = MagicMock()
    session.query.return_value.order_by.return_value.all.return_value = []

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/arbitrage/v3/top10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_get_top10_returns_rows_from_db():
    row = ArbitrageTop10Current(
        rank=1,
        scrape_run_id=6,
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
        legs=[
            {"role": "over", "bookmaker": "betano", "odd": 1.34},
            {"role": "under", "bookmaker": "efbet", "odd": 4.78},
        ],
        captured_at=datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc),
    )
    session = MagicMock()
    session.query.return_value.order_by.return_value.all.return_value = [row]

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/arbitrage/v3/top10")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rank"] == 1
    assert data[0]["match"] == "France vs Morocco"
    assert data[0]["margin_pct"] == 4.66
    assert data[0]["legs"][0]["bookmaker"] == "betano"


def test_post_run_triggers_pipeline(client, monkeypatch):
    captured: dict = {}

    def fake_run_pipeline_v3(session, **kwargs):
        captured.update(kwargs)
        return {
            "run_id": 7,
            "status": "success",
            "stats": {"matches_linked": 3},
            "errors": None,
            "top10": [],
        }

    monkeypatch.setattr("api.routes.arbitrage_v3.run_pipeline_v3", fake_run_pipeline_v3)

    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.post(
            "/arbitrage/v3/run",
            params={
                "competition": "world-cup-2026",
                "time_window": "world_cup",
                "min_margin": 1.5,
                "limit": 10,
                "rules": ["total_goals_ou", "both_teams_to_score"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == 7
    assert body["status"] == "success"
    assert captured["triggered_by"] == "api"
    assert captured["competition_slug"] == "world-cup-2026"
    assert captured["min_margin"] == 1.5
    assert captured["rule_slugs"] == ["total_goals_ou", "both_teams_to_score"]


def test_post_run_returns_400_on_pipeline_error(client, monkeypatch):
    def fake_run_pipeline_v3(*_args, **_kwargs):
        raise ValueError("Competition not found: missing")

    monkeypatch.setattr("api.routes.arbitrage_v3.run_pipeline_v3", fake_run_pipeline_v3)

    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.post("/arbitrage/v3/run", params={"competition": "missing"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Competition not found: missing"
