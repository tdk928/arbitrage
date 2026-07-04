-- Query total_goals_ou from latest scrape run.
-- Filter by match in WHERE clause (example: Canada vs Morocco).

WITH latest AS (
    SELECT id FROM scrape_runs_v3
    WHERE status IN ('success', 'partial')
    ORDER BY id DESC LIMIT 1
)
SELECT
    rs.slug AS rule,
    ht.name AS home,
    at.name AS away,
    m.kickoff_utc,
    b.slug AS bookmaker,
    o.ui_label,
    o.line,
    o.external_event_id,
    (SELECT e->>'odd' FROM jsonb_array_elements(o.outcomes) e WHERE e->>'role' = 'over') AS over_odd,
    (SELECT e->>'odd' FROM jsonb_array_elements(o.outcomes) e WHERE e->>'role' = 'under') AS under_odd
FROM market_odds_v3 o
JOIN latest l ON l.id = o.scrape_run_id
JOIN market_rule_sets rs ON rs.id = o.rule_set_id
JOIN matches m ON m.id = o.match_id
JOIN teams ht ON ht.id = m.home_team_id
JOIN teams at ON at.id = m.away_team_id
JOIN bookmakers b ON b.id = o.bookmaker_id
WHERE rs.slug = 'total_goals_ou'
ORDER BY ht.name, at.name, b.slug, o.line::numeric;
