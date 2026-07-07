-- Scrape runs + rule-matched odds snapshots.

CREATE TABLE scrape_runs_v3 (
    id SERIAL PRIMARY KEY,
    competition_slug VARCHAR(64) NOT NULL,
    time_window VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'running',
    triggered_by VARCHAR(16) NOT NULL DEFAULT 'cli',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    stats JSONB NOT NULL DEFAULT '{}',
    notes TEXT
);

CREATE TABLE market_odds_v3 (
    id SERIAL PRIMARY KEY,
    scrape_run_id INTEGER NOT NULL REFERENCES scrape_runs_v3(id) ON DELETE CASCADE,
    rule_set_id INTEGER NOT NULL REFERENCES market_rule_sets(id) ON DELETE CASCADE,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    line VARCHAR(16) NOT NULL,
    market_name VARCHAR(256) NOT NULL,
    external_event_id VARCHAR(64),
    ui_label VARCHAR(256),
    outcomes JSONB NOT NULL DEFAULT '[]',
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scrape_run_id, rule_set_id, match_id, bookmaker_id, line)
);

CREATE INDEX idx_scrape_runs_v3_started ON scrape_runs_v3(started_at DESC);
CREATE INDEX idx_market_odds_v3_run_rule ON market_odds_v3(scrape_run_id, rule_set_id);
CREATE INDEX idx_market_odds_v3_match ON market_odds_v3(match_id, rule_set_id);
