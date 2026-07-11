from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.arbitrage_v3 import get_db, router
from api.routes.auth import get_current_user, require_admin
from scraper.models_auth import Role, User

app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    return TestClient(app)


def _admin_user() -> User:
    role = Role(id=2, slug="admin", name="Admin")
    return User(
        id=1,
        email="admin@example.com",
        password_hash="hashed",
        role_id=role.id,
        role=role,
    )


def _override_admin():
    app.dependency_overrides[require_admin] = lambda: _admin_user()


def _client_user() -> User:
    role = Role(id=1, slug="client", name="Client")
    return User(
        id=2,
        email="user@example.com",
        password_hash="hashed",
        role_id=role.id,
        role=role,
    )


def test_delete_audit_requires_auth(client):
    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.request(
            "DELETE",
            "/arbitrage/v3/audit",
            json={
                "run_id": 10,
                "rule_slug": "total_goals_ou",
                "home_team": "Spain",
                "away_team": "Belgium",
                "line": "0.5",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_delete_audit_forbidden_for_client(client):
    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _client_user()
    try:
        response = client.request(
            "DELETE",
            "/arbitrage/v3/audit",
            json={
                "run_id": 10,
                "rule_slug": "total_goals_ou",
                "home_team": "Spain",
                "away_team": "Belgium",
                "line": "0.5",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_delete_audit_returns_404_when_missing(client, monkeypatch):
    session = MagicMock()

    def override_db():
        yield session

    monkeypatch.setattr("api.routes.arbitrage_v3.delete_audit_entry", lambda *_a, **_k: False)

    app.dependency_overrides[get_db] = override_db
    _override_admin()
    try:
        response = client.request(
            "DELETE",
            "/arbitrage/v3/audit",
            json={
                "run_id": 10,
                "rule_slug": "total_goals_ou",
                "home_team": "Spain",
                "away_team": "Belgium",
                "line": "0.5",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit entry not found"


def test_delete_audit_returns_204_when_deleted(client, monkeypatch):
    session = MagicMock()

    def override_db():
        yield session

    monkeypatch.setattr("api.routes.arbitrage_v3.delete_audit_entry", lambda *_a, **_k: True)

    app.dependency_overrides[get_db] = override_db
    _override_admin()
    try:
        response = client.request(
            "DELETE",
            "/arbitrage/v3/audit",
            json={
                "run_id": 10,
                "rule_slug": "total_goals_ou",
                "home_team": "Spain",
                "away_team": "Belgium",
                "line": "0.5",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""


def test_delete_top10_requires_auth(client):
    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.delete("/arbitrage/v3/top10/3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_delete_top10_forbidden_for_client(client):
    session = MagicMock()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _client_user()
    try:
        response = client.delete(
            "/arbitrage/v3/top10/3",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_delete_top10_returns_404_when_missing(client, monkeypatch):
    session = MagicMock()

    def override_db():
        yield session

    monkeypatch.setattr("api.routes.arbitrage_v3.delete_top10_rank", lambda *_a, **_k: False)

    app.dependency_overrides[get_db] = override_db
    _override_admin()
    try:
        response = client.delete("/arbitrage/v3/top10/3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Top 10 entry not found"


def test_delete_top10_returns_204_when_deleted(client, monkeypatch):
    session = MagicMock()

    def override_db():
        yield session

    monkeypatch.setattr("api.routes.arbitrage_v3.delete_top10_rank", lambda *_a, **_k: True)

    app.dependency_overrides[get_db] = override_db
    _override_admin()
    try:
        response = client.delete("/arbitrage/v3/top10/3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
