-- Cross-bookmaker match linking.

CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    name_normalized VARCHAR(128) NOT NULL,
    country_code VARCHAR(8)
);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    kickoff_utc TIMESTAMPTZ NOT NULL,
    canonical_key VARCHAR(64) NOT NULL,
    external_ids JSONB NOT NULL DEFAULT '{}',
    UNIQUE (competition_id, canonical_key)
);

CREATE INDEX idx_matches_kickoff ON matches(kickoff_utc);
