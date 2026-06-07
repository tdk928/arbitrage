-- Database arbitrage is created by docker-compose POSTGRES_DB

CREATE TABLE IF NOT EXISTS market_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    outcome_count SMALLINT NOT NULL,
    line VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS bookmakers (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS competitions (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    sport VARCHAR(32) NOT NULL DEFAULT 'football',
    season VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS competition_sources (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    discovery_type VARCHAR(32) NOT NULL,
    discovery_config JSONB NOT NULL DEFAULT '{}',
    listing_url TEXT,
    UNIQUE (competition_id, bookmaker_id)
);

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    name_normalized VARCHAR(128) NOT NULL,
    country_code VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    kickoff_utc TIMESTAMPTZ NOT NULL,
    canonical_key VARCHAR(64) NOT NULL,
    external_ids JSONB NOT NULL DEFAULT '{}',
    UNIQUE (competition_id, canonical_key)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    competition_slug VARCHAR(64) NOT NULL,
    time_window VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'running',
    triggered_by VARCHAR(16) NOT NULL DEFAULT 'cli',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    market_type_id INTEGER NOT NULL REFERENCES market_types(id),
    outcomes JSONB NOT NULL DEFAULT '[]',
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    market_type_id INTEGER NOT NULL REFERENCES market_types(id),
    margin_pct NUMERIC(8, 4) NOT NULL,
    implied_total NUMERIC(10, 6) NOT NULL,
    legs JSONB NOT NULL,
    bookmaker_count SMALLINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_kickoff ON matches(kickoff_utc);
CREATE INDEX IF NOT EXISTS idx_odds_run_match ON odds_snapshots(scrape_run_id, match_id);
CREATE INDEX IF NOT EXISTS idx_arb_run_margin ON arbitrage_opportunities(scrape_run_id, margin_pct DESC);
