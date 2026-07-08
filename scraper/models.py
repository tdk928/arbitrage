from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MarketType(Base):
    __tablename__ = "market_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    line: Mapped[Optional[str]] = mapped_column(String(16))


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


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    time_window: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running")
    triggered_by: Mapped[str] = mapped_column(String(16), default="cli")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id"), nullable=False)
    market_type_id: Mapped[int] = mapped_column(ForeignKey("market_types.id"), nullable=False)
    outcomes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class ArbitrageOpportunity(Base):
    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    market_type_id: Mapped[int] = mapped_column(ForeignKey("market_types.id"), nullable=False)
    margin_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    implied_total: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    bookmaker_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
