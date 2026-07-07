-- Current top-10 arbitrage snapshot (replaced each scrape; max 10 rows).
-- Denormalized match fields so rows survive ephemeral match/odds cleanup.

CREATE TABLE arbitrage_top10_current (
    rank SMALLINT PRIMARY KEY CHECK (rank >= 1 AND rank <= 10),
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs_v3(id) ON DELETE CASCADE,
    rule_set_id INTEGER NOT NULL REFERENCES market_rule_sets(id) ON DELETE CASCADE,
    rule_slug VARCHAR(64) NOT NULL,
    line VARCHAR(16),
    margin_pct NUMERIC(8, 4) NOT NULL,
    implied_total NUMERIC(10, 6) NOT NULL,
    bookmaker_count SMALLINT NOT NULL,
    home_team VARCHAR(128) NOT NULL,
    away_team VARCHAR(128) NOT NULL,
    kickoff_utc TIMESTAMPTZ,
    market_label VARCHAR(256) NOT NULL,
    legs JSONB NOT NULL DEFAULT '[]',
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_arbitrage_top10_current_run ON arbitrage_top10_current(scrape_run_id);

-- Append-only audit history (top 10 per scrape; never wiped by scraper).

CREATE TABLE arbitrage_audit (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER REFERENCES scrape_runs_v3(id) ON DELETE SET NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rank SMALLINT NOT NULL CHECK (rank >= 1 AND rank <= 10),
    rule_set_id INTEGER REFERENCES market_rule_sets(id) ON DELETE SET NULL,
    rule_slug VARCHAR(64) NOT NULL,
    line VARCHAR(16),
    margin_pct NUMERIC(8, 4) NOT NULL,
    implied_total NUMERIC(10, 6) NOT NULL,
    bookmaker_count SMALLINT NOT NULL,
    home_team VARCHAR(128) NOT NULL,
    away_team VARCHAR(128) NOT NULL,
    kickoff_utc TIMESTAMPTZ,
    market_label VARCHAR(256) NOT NULL,
    legs JSONB NOT NULL DEFAULT '[]'
);

CREATE INDEX idx_arbitrage_audit_captured_at ON arbitrage_audit(captured_at DESC);
CREATE INDEX idx_arbitrage_audit_run ON arbitrage_audit(scrape_run_id);
