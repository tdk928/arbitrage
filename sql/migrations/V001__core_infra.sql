-- Bookmakers + competition discovery config (required to scrape).

CREATE TABLE bookmakers (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE competitions (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    sport VARCHAR(32) NOT NULL DEFAULT 'football',
    season VARCHAR(32)
);

CREATE TABLE competition_sources (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    bookmaker_id INTEGER NOT NULL REFERENCES bookmakers(id) ON DELETE CASCADE,
    discovery_type VARCHAR(32) NOT NULL,
    discovery_config JSONB NOT NULL DEFAULT '{}',
    listing_url TEXT,
    UNIQUE (competition_id, bookmaker_id)
);
