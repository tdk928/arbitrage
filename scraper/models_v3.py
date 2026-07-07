from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scraper.models import Base


class MarketRuleSet(Base):
    __tablename__ = "market_rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    outcome_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    scope: Mapped[str] = mapped_column(String(32), default="global")
    line_filter: Mapped[str] = mapped_column(String(32), default="half_only")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    site_matches: Mapped[list["MarketRuleSiteMatch"]] = relationship(back_populates="rule_set")


class MarketRuleSiteMatch(Base):
    __tablename__ = "market_rule_site_matches"
    __table_args__ = (UniqueConstraint("rule_set_id", "bookmaker_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("market_rule_sets.id"), nullable=False)
    bookmaker_slug: Mapped[str] = mapped_column(String(32), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    match_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ui_label: Mapped[Optional[str]] = mapped_column(String(256))
    priority: Mapped[int] = mapped_column(SmallInteger, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rule_set: Mapped["MarketRuleSet"] = relationship(back_populates="site_matches")


class ScrapeRunV3(Base):
    __tablename__ = "scrape_runs_v3"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competition_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    time_window: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="running")
    triggered_by: Mapped[str] = mapped_column(String(16), default="cli")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class MarketOddsV3(Base):
    __tablename__ = "market_odds_v3"
    __table_args__ = (
        UniqueConstraint("scrape_run_id", "rule_set_id", "match_id", "bookmaker_id", "line"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs_v3.id"), nullable=False)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("market_rule_sets.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("bookmakers.id"), nullable=False)
    line: Mapped[str] = mapped_column(String(16), nullable=False)
    market_name: Mapped[str] = mapped_column(String(256), nullable=False)
    external_event_id: Mapped[Optional[str]] = mapped_column(String(64))
    ui_label: Mapped[Optional[str]] = mapped_column(String(256))
    outcomes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArbitrageTop10Current(Base):
    __tablename__ = "arbitrage_top10_current"

    rank: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs_v3.id"), nullable=False)
    rule_set_id: Mapped[int] = mapped_column(ForeignKey("market_rule_sets.id"), nullable=False)
    rule_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    line: Mapped[Optional[str]] = mapped_column(String(16))
    margin_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    implied_total: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    bookmaker_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    home_team: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team: Mapped[str] = mapped_column(String(128), nullable=False)
    kickoff_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    market_label: Mapped[str] = mapped_column(String(256), nullable=False)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArbitrageAudit(Base):
    __tablename__ = "arbitrage_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrape_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scrape_runs_v3.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rule_set_id: Mapped[Optional[int]] = mapped_column(ForeignKey("market_rule_sets.id"))
    rule_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    line: Mapped[Optional[str]] = mapped_column(String(16))
    margin_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    implied_total: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    bookmaker_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    home_team: Mapped[str] = mapped_column(String(128), nullable=False)
    away_team: Mapped[str] = mapped_column(String(128), nullable=False)
    kickoff_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    market_label: Mapped[str] = mapped_column(String(256), nullable=False)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
