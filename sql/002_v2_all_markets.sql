-- V2 schema: all-markets pipeline (parallel to v1; does not alter v1 tables)

CREATE TABLE IF NOT EXISTS scrape_runs_v2 (
    id SERIAL PRIMARY KEY,
    competition_slug VARCHAR(64) NOT NULL,
    time_window VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'running',
    triggered_by VARCHAR(16) NOT NULL DEFAULT 'cli',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    notes TEXT,
    stats JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS canonical_markets_v2 (
    id SERIAL PRIMARY KEY,
    canonical_key VARCHAR(64) NOT NULL UNIQUE,
    family VARCHAR(64) NOT NULL,
    period VARCHAR(16) NOT NULL DEFAULT 'ft',
    scope VARCHAR(32) NOT NULL DEFAULT 'match',
    line VARCHAR(16),
    outcome_roles JSONB NOT NULL DEFAULT '[]',
    label VARCHAR(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_markets_v2 (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs_v2(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    canonical_market_id INTEGER REFERENCES canonical_markets_v2(id),
    external_market_id VARCHAR(128),
    market_name VARCHAR(256) NOT NULL,
    provider_template VARCHAR(128),
    specifiers JSONB NOT NULL DEFAULT '{}',
    outcomes JSONB NOT NULL DEFAULT '[]',
    raw_payload JSONB,
    mapped BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS odds_snapshots_v2 (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs_v2(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    canonical_market_id INTEGER NOT NULL REFERENCES canonical_markets_v2(id) ON DELETE CASCADE,
    outcomes JSONB NOT NULL DEFAULT '[]',
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scrape_run_id, match_id, bookmaker_id, canonical_market_id)
);

CREATE TABLE IF NOT EXISTS arbitrage_opportunities_v2 (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs_v2(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    canonical_market_id INTEGER NOT NULL REFERENCES canonical_markets_v2(id) ON DELETE CASCADE,
    margin_pct NUMERIC(8, 4) NOT NULL,
    implied_total NUMERIC(10, 6) NOT NULL,
    legs JSONB NOT NULL,
    bookmaker_count SMALLINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_markets_v2_run ON raw_markets_v2(scrape_run_id);
CREATE INDEX IF NOT EXISTS idx_odds_v2_run_match ON odds_snapshots_v2(scrape_run_id, match_id);
CREATE INDEX IF NOT EXISTS idx_arb_v2_run_margin ON arbitrage_opportunities_v2(scrape_run_id, margin_pct DESC);
CREATE INDEX IF NOT EXISTS idx_canonical_v2_family ON canonical_markets_v2(family, period, line);
