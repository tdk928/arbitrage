from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy.orm import Session, joinedload

from scraper.config import get_settings
from scraper.models_auth import Role, User

ALGORITHM = "HS256"
CLIENT_ROLE_SLUG = "client"
ADMIN_ROLE_SLUG = "admin"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def is_subscription_active(user: User, *, now: datetime | None = None) -> bool:
    return user.has_active_subscription(now=now)


def create_access_token(user: User, *, now: datetime | None = None) -> tuple[str, int]:
    settings = get_settings()
    current = now or datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    expires_at = current + expires_delta
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.slug,
        "has_active_subscription": is_subscription_active(user, now=current),
        "iat": int(current.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .one_or_none()
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == email)
        .one_or_none()
    )


def get_client_role(db: Session) -> Role:
    role = db.query(Role).filter(Role.slug == CLIENT_ROLE_SLUG).one_or_none()
    if role is None:
        raise RuntimeError(f"Required role '{CLIENT_ROLE_SLUG}' is missing from database")
    return role


def register_user(db: Session, email: str, password: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise ValueError("Email is already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        role_id=get_client_role(db).id,
    )
    db.add(user)
    db.commit()
    reloaded = get_user_by_email(db, email)
    assert reloaded is not None
    return reloaded


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def list_all_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .options(joinedload(User.role))
        .order_by(User.id)
        .all()
    )


def update_user_profile(db: Session, email: str, updates: dict) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    if "phone" in updates:
        user.phone = updates["phone"]
    if "active_from" in updates:
        user.active_from = updates["active_from"]
    if "active_to" in updates:
        user.active_to = updates["active_to"]

    active_from = user.active_from
    active_to = user.active_to
    if active_from is not None and active_to is not None and active_from > active_to:
        raise ValueError("valid_from must be before or equal to valid_to")

    db.commit()
    return get_user_by_email(db, email)


def activate_user_for_24h(db: Session, email: str, *, now: datetime | None = None) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    current = now or datetime.now(timezone.utc)
    user.active_from = current
    user.active_to = current + timedelta(hours=24)
    db.commit()
    return get_user_by_email(db, email)


def deactivate_user(db: Session, email: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    user.active_from = None
    user.active_to = None
    db.commit()
    return get_user_by_email(db, email)
