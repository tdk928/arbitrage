-- Curated cross-bookmaker market rules (v3 source of truth).

CREATE TABLE market_rule_sets (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    label VARCHAR(256) NOT NULL,
    description TEXT,
    outcome_roles JSONB NOT NULL DEFAULT '["over", "under"]',
    scope VARCHAR(32) NOT NULL DEFAULT 'global',
    line_filter VARCHAR(32) NOT NULL DEFAULT 'half_only',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE market_rule_site_matches (
    id SERIAL PRIMARY KEY,
    rule_set_id INTEGER NOT NULL REFERENCES market_rule_sets(id) ON DELETE CASCADE,
    bookmaker_slug VARCHAR(32) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    match_criteria JSONB NOT NULL DEFAULT '{}',
    ui_label VARCHAR(256),
    priority SMALLINT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rule_set_id, bookmaker_slug)
);

CREATE INDEX idx_market_rule_sets_active ON market_rule_sets(scope, is_active);
CREATE INDEX idx_market_rule_site_bm ON market_rule_site_matches(bookmaker_slug, is_active);
