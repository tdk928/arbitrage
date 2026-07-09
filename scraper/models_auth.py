from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scraper.models import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    active_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    active_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    phone: Mapped[Optional[str]] = mapped_column(String(32))

    role: Mapped[Role] = relationship(back_populates="users")

    def has_active_subscription(self, *, now: datetime | None = None) -> bool:
        if self.active_from is None or self.active_to is None:
            return False
        current = now or datetime.now(timezone.utc)

        def _as_utc(value: datetime) -> datetime:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        return _as_utc(self.active_from) <= current <= _as_utc(self.active_to)
