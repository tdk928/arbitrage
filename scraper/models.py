from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Bookmaker(Base):
    __tablename__ = "bookmakers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sport: Mapped[str] = mapped_column(String(32), default="football")
    season: Mapped[Optional[str]] = mapped_column(String(32))

    sources: Mapped[list["CompetitionSource"]] = relationship(back_populates="competition")


class CompetitionSource(Base):
    __tablename__ = "competition_sources"
    __table_args__ = (UniqueConstraint("competition_id", "bookmaker_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id"), nullable=False)
    discovery_type: Mapped[str] = mapped_column(String(32), nullable=False)
    discovery_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    listing_url: Mapped[Optional[str]] = mapped_column(Text)

    competition: Mapped["Competition"] = relationship(back_populates="sources")
    bookmaker: Mapped["Bookmaker"] = relationship()


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(128), nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(8))


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("competition_id", "canonical_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(64), nullable=False)
    external_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
