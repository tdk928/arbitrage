from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session, sessionmaker

from scraper.auth_service import (
    ADMIN_ROLE_SLUG,
    activate_user_for_24h,
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_id,
    list_all_users,
    register_user,
    update_user_profile,
)
from scraper.db import get_engine, init_db
from scraper.models_auth import User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()

_engine = None
_SessionLocal = None


def _get_session_factory():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        init_db()
        _engine = get_engine()
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal


def get_db():
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserListItem(BaseModel):
    email: EmailStr
    role: Literal["client", "admin"]
    phone: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class UserListResponse(BaseModel):
    count: int
    users: list[UserListItem]


class UserUpdateRequest(BaseModel):
    phone: Optional[str] = Field(default=None, max_length=32)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.slug != ADMIN_ROLE_SLUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _user_to_list_item(user: User) -> UserListItem:
    return UserListItem(
        email=user.email,
        role=user.role.slug,
        phone=user.phone,
        valid_from=user.active_from,
        valid_to=user.active_to,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_user(db, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    access_token, expires_in = create_access_token(user)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, expires_in = create_access_token(user)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/users", response_model=UserListResponse)
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = list_all_users(db)
    items = [_user_to_list_item(user) for user in users]
    return UserListResponse(count=len(items), users=items)


@router.patch("/users/{email}", response_model=UserListItem)
def update_user(
    email: EmailStr,
    body: UserUpdateRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    field_map = {
        "phone": "phone",
        "valid_from": "active_from",
        "valid_to": "active_to",
    }
    db_updates = {field_map[key]: value for key, value in updates.items()}

    try:
        user = update_user_profile(db, str(email), db_updates)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_list_item(user)


@router.post("/users/{email}/activate", response_model=UserListItem)
def activate_user(
    email: EmailStr,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = activate_user_for_24h(db, str(email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_list_item(user)
