-- Refactor arbitrage_audit: rolling top-20 by margin_pct, one row per match+market event.

ALTER TABLE arbitrage_audit DROP CONSTRAINT IF EXISTS arbitrage_audit_rank_check;
ALTER TABLE arbitrage_audit DROP COLUMN IF EXISTS rank;

ALTER TABLE arbitrage_audit ADD COLUMN IF NOT EXISTS event_key VARCHAR(512);

UPDATE arbitrage_audit
SET event_key = LOWER(TRIM(home_team)) || '|' || LOWER(TRIM(away_team)) || '|' ||
    COALESCE(to_char(kickoff_utc AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') || '|' ||
    rule_slug || '|' || COALESCE(line, '')
WHERE event_key IS NULL OR event_key = '';

DELETE FROM arbitrage_audit a
USING arbitrage_audit b
WHERE a.event_key = b.event_key
  AND (
    a.margin_pct < b.margin_pct
    OR (a.margin_pct = b.margin_pct AND a.id < b.id)
  );

DELETE FROM arbitrage_audit
WHERE id NOT IN (
    SELECT id FROM arbitrage_audit ORDER BY margin_pct DESC, id ASC LIMIT 20
);

ALTER TABLE arbitrage_audit ALTER COLUMN event_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_arbitrage_audit_event_key ON arbitrage_audit(event_key);
CREATE INDEX IF NOT EXISTS idx_arbitrage_audit_margin_pct ON arbitrage_audit(margin_pct DESC);
