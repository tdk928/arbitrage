from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from scraper.config import get_settings
from scraper.models import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_session() -> Generator[Session, None, None]:
    get_engine()
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
