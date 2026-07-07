from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from scraper.models import Base


class ScrapeRunV2(Base):
    __tablename__ = "scrape_runs_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    time_window: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running")
    triggered_by: Mapped[str] = mapped_column(String(16), default="cli")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class CanonicalMarketV2(Base):
    __tablename__ = "canonical_markets_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[str] = mapped_column(String(16), default="ft")
    scope: Mapped[str] = mapped_column(String(32), default="match")
    line: Mapped[Optional[str]] = mapped_column(String(16))
    outcome_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    label: Mapped[str] = mapped_column(String(256), nullable=False)


class RawMarketV2(Base):
    __tablename__ = "raw_markets_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs_v2.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id"), nullable=False)
    canonical_market_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("canonical_markets_v2.id")
    )
    external_market_id: Mapped[Optional[str]] = mapped_column(String(128))
    market_name: Mapped[str] = mapped_column(String(256), nullable=False)
    provider_template: Mapped[Optional[str]] = mapped_column(String(128))
    specifiers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    outcomes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    mapped: Mapped[bool] = mapped_column(Boolean, default=False)


class OddsSnapshotV2(Base):
    __tablename__ = "odds_snapshots_v2"
    __table_args__ = (
        UniqueConstraint(
            "scrape_run_id",
            "match_id",
            "bookmaker_id",
            "canonical_market_id",
            name="uq_odds_v2_run_match_bm_canonical",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs_v2.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id"), nullable=False)
    canonical_market_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_markets_v2.id"), nullable=False
    )
    outcomes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ArbitrageOpportunityV2(Base):
    __tablename__ = "arbitrage_opportunities_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs_v2.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    canonical_market_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_markets_v2.id"), nullable=False
    )
    margin_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    implied_total: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    bookmaker_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
