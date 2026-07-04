# Market Rules v3

Curated cross-bookmaker mapping stored in **Postgres**. Calibrated bet types (not teams).

## Schema (Flyway migrations)

See `sql/README.md`. Migrations are CREATE-only (`V001`–`V004`).

## Rule #1: `total_goals_ou`

Over/Under match total goals. **Lines: .5 only** (0.5, 1.5, 2.5 …). No .25/.75, no whole 1/2/3.

| Bookmaker | UI label | Platform |
|-----------|----------|----------|
| winbet | Алт. Брой Голове | egt |
| inbet | Алт. Брой Голове | egt (same criteria as winbet) |
| efbet | Голове в Мача | efbet |
| palmsbet | Общ брой голове | altenar (typeId 18) |
| 8888 | Брой Голове | sportinno |

## Setup (fresh DB)

```bash
python -m scraper.migrate
python -m scraper.seed
python -m scraper.seed_market_rules
python -m scraper.run_v3_scrape
```

## Query from DB (no re-scrape)

```bash
python -m scraper.query_v3_market total_goals_ou --home Canada --away Morocco
```

Or SQL: `sql/queries/query_total_goals_ou.sql`

## API

```bash
GET  /arbitrage/v3/rules
GET  /arbitrage/v3/rules/total_goals_ou/sites
POST /arbitrage/v3/rules/seed
```
