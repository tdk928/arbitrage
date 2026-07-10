from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.auth import get_current_user, get_db, require_admin, router
from scraper.models_auth import Role, User

app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    return TestClient(app)


def _make_user(
    *,
    email: str = "user@example.com",
    role_slug: str = "client",
    active_from: datetime | None = None,
    active_to: datetime | None = None,
) -> User:
    role = Role(id=1 if role_slug == "client" else 2, slug=role_slug, name=role_slug.title())
    return User(
        id=1,
        email=email,
        password_hash="hashed",
        role_id=role.id,
        registered_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
        active_from=active_from,
        active_to=active_to,
        role=role,
    )


def test_register_returns_token(client):
    session = MagicMock()
    user = _make_user()

    def override_db():
        yield session

    with (
        patch("api.routes.auth.register_user", return_value=user) as register_mock,
        patch("api.routes.auth.create_access_token", return_value=("token-123", 3600)) as token_mock,
    ):
        app.dependency_overrides[get_db] = override_db
        try:
            response = client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "secret123"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "access_token": "token-123",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    register_mock.assert_called_once_with(session, "user@example.com", "secret123")
    token_mock.assert_called_once_with(user)


def test_register_rejects_duplicate_email(client):
    session = MagicMock()

    def override_db():
        yield session

    with patch("api.routes.auth.register_user", side_effect=ValueError("Email is already registered")):
        app.dependency_overrides[get_db] = override_db
        try:
            response = client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "secret123"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_login_returns_token_for_valid_credentials(client):
    session = MagicMock()
    user = _make_user(role_slug="admin")

    def override_db():
        yield session

    with (
        patch("api.routes.auth.authenticate_user", return_value=user) as auth_mock,
        patch("api.routes.auth.create_access_token", return_value=("admin-token", 3600)),
    ):
        app.dependency_overrides[get_db] = override_db
        try:
            response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "secret123"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "admin-token"
    auth_mock.assert_called_once_with(session, "user@example.com", "secret123")


def test_login_rejects_invalid_credentials(client):
    session = MagicMock()

    def override_db():
        yield session

    with patch("api.routes.auth.authenticate_user", return_value=None):
        app.dependency_overrides[get_db] = override_db
        try:
            response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_create_access_token_includes_role_and_subscription_flag():
    from scraper.auth_service import create_access_token

    now = datetime.now(timezone.utc)
    active_user = _make_user(
        active_from=now - timedelta(hours=1),
        active_to=now + timedelta(hours=1),
    )
    inactive_user = _make_user()

    with patch("scraper.auth_service.get_settings") as settings_mock:
        settings_mock.return_value.jwt_secret = "test-secret"
        settings_mock.return_value.jwt_expire_minutes = 60

        active_token, _ = create_access_token(active_user, now=now)
        inactive_token, _ = create_access_token(inactive_user, now=now)

    from jose import jwt

    active_payload = jwt.decode(active_token, "test-secret", algorithms=["HS256"])
    inactive_payload = jwt.decode(inactive_token, "test-secret", algorithms=["HS256"])

    assert active_payload["role"] == "client"
    assert active_payload["has_active_subscription"] is True
    assert inactive_payload["has_active_subscription"] is False


def test_password_is_hashed_and_verified():
    from scraper.auth_service import hash_password, verify_password

    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_list_users_returns_dto_for_admin(client):
    session = MagicMock()
    now = datetime.now(timezone.utc)
    admin = _make_user(role_slug="admin", email="admin@example.com")
    client_user = _make_user(email="client@example.com")
    client_user.id = 2
    client_user.phone = "+359888123456"
    client_user.active_from = now - timedelta(days=1)
    client_user.active_to = now + timedelta(days=1)

    def override_db():
        yield session

    with patch("api.routes.auth.list_all_users", return_value=[admin, client_user]):
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[require_admin] = lambda: admin
        try:
            response = client.get(
                "/auth/users",
                headers={"Authorization": "Bearer admin-token"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["users"][1] == {
        "email": "client@example.com",
        "phone": "+359888123456",
        "valid_from": client_user.active_from.isoformat().replace("+00:00", "Z"),
        "valid_to": client_user.active_to.isoformat().replace("+00:00", "Z"),
    }


def test_list_users_rejects_non_admin(client):
    session = MagicMock()
    client_user = _make_user(role_slug="client")

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: client_user
    try:
        response = client.get(
            "/auth/users",
            headers={"Authorization": "Bearer client-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

