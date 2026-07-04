# SQL migrations (Flyway-style)

Versioned **CREATE** migrations live in `sql/migrations/`:

```
V001__core_infra.sql          bookmakers, competitions, competition_sources
V002__teams_and_matches.sql   teams, matches
V003__market_rules.sql        market_rule_sets, market_rule_site_matches
V004__scrape_storage.sql      scrape_runs_v3, market_odds_v3
V005__arbitrage_top10_and_audit.sql  arbitrage_top10_current, arbitrage_audit
```

Migrations are **CREATE-only**. No DROP scripts in this folder.

## Apply

```bash
python -m scraper.migrate
python -m scraper.migrate --dry-run
```

Applied scripts are tracked in `flyway_schema_history` (checksum-validated).
To change schema after deploy, add `V005__...sql` — never edit applied files.

## Fresh start on an existing DB (one-time, manual)

Legacy cleanup is **outside** Flyway:

```bash
psql $DATABASE_URL -f sql/bootstrap/drop_legacy_once.sql
python -m scraper.migrate
python -m scraper.seed
python -m scraper.seed_market_rules
python -m scraper.run_v3_scrape
```

## Ad-hoc queries

`sql/queries/` — read-only SQL, not migrations.
