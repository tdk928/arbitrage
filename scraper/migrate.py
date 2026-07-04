"""Flyway-style SQL migrations (V001__description.sql)."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text

from scraper.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql" / "migrations"
VERSION_RE = re.compile(r"^V(\d+)__(.+)\.sql$")

HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS flyway_schema_history (
    installed_rank SERIAL PRIMARY KEY,
    version VARCHAR(32) NOT NULL UNIQUE,
    description VARCHAR(256) NOT NULL,
    script VARCHAR(512) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    installed_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE
);
"""


@dataclass(frozen=True)
class Migration:
    version: str
    description: str
    path: Path

    @property
    def version_num(self) -> int:
        return int(self.version)


def _discover_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(MIGRATIONS_DIR.glob("V*.sql")):
        match = VERSION_RE.match(path.name)
        if not match:
            continue
        ver, desc = match.groups()
        migrations.append(
            Migration(version=ver, description=desc.replace("_", " "), path=path)
        )
    migrations.sort(key=lambda m: m.version_num)
    return migrations


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _ensure_history(conn) -> None:
    conn.execute(text(HISTORY_DDL))


def _applied_versions(conn) -> dict[str, str]:
    rows = conn.execute(
        text("SELECT version, checksum FROM flyway_schema_history WHERE success = TRUE")
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def migrate(*, dry_run: bool = False) -> list[str]:
    if not MIGRATIONS_DIR.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {MIGRATIONS_DIR}")

    migrations = _discover_migrations()
    if not migrations:
        raise RuntimeError("No migration scripts found")

    engine = _get_engine()
    applied: list[str] = []

    with engine.begin() as conn:
        _ensure_history(conn)
        done = _applied_versions(conn)

        for migration in migrations:
            sql = migration.path.read_text(encoding="utf-8")
            cs = _checksum(sql)

            if migration.version in done:
                if done[migration.version] != cs:
                    raise RuntimeError(
                        f"Checksum mismatch for V{migration.version} "
                        f"({migration.path.name}). "
                        "Create a new migration instead of editing applied scripts."
                    )
                continue

            if dry_run:
                applied.append(f"V{migration.version} (dry-run)")
                continue

            start = time.perf_counter()
            conn.execute(text(sql))
            elapsed = int((time.perf_counter() - start) * 1000)

            conn.execute(
                text(
                    """
                    INSERT INTO flyway_schema_history
                        (version, description, script, checksum, execution_time_ms, success)
                    VALUES
                        (:version, :description, :script, :checksum, :elapsed, TRUE)
                    """
                ),
                {
                    "version": migration.version,
                    "description": migration.description,
                    "script": migration.path.name,
                    "checksum": cs,
                    "elapsed": elapsed,
                },
            )
            applied.append(f"V{migration.version} {migration.description} ({elapsed}ms)")

    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply Flyway-style SQL migrations")
    parser.add_argument("--dry-run", action="store_true", help="List pending migrations only")
    args = parser.parse_args(argv)

    try:
        applied = migrate(dry_run=args.dry_run)
    except Exception as exc:
        print(f"migrate failed: {exc}", file=sys.stderr)
        return 1

    if not applied:
        print("Database schema is up to date.")
    else:
        for line in applied:
            print(f"Applied {line}" if not args.dry_run else f"Pending {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
