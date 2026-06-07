# Arbitrage Scraper

Python service that scrapes odds from 6 Bulgarian/international bookmakers, stores them in PostgreSQL (`arbitrage`), and finds cross-bookmaker arbitrage opportunities.

## Bookmakers

| Site | Platform |
|------|----------|
| bet365 | HTML hub |
| winbet | EGT Digital |
| inbet | EGT Digital |
| palmsbet | Altenar |
| 8888 | SportInno (`curl_cffi`); Altenar bridge until WC is live on SportInno |
| efbet | efbet gateway |

## Markets

- 1/X/2
- Over/Under 2.5 goals
- Corners Over/Under 8.5 and 9.5

## Quick start

```bash
cd arbitrage
cp .env.example .env   # set DATABASE_URL for your Postgres user
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Option A: local Postgres (create DB first: createdb arbitrage)
export DATABASE_URL="postgresql://YOUR_USER@localhost:5432/arbitrage"

# Option B: Docker
docker compose up -d

# Create tables + seed bookmakers/competition config
python -m scraper.db_init   # or: python -c "from scraper.db import init_db; init_db()"
python -m scraper.seed
```

**8888 note:** SportInno blocks plain `httpx` requests (TLS fingerprinting). The scraper uses `curl_cffi` to impersonate Chrome. While 8888's WC page shows "Очаквайте скоро", fixtures/odds fall back to their Altenar feed (`8888.bg` integration). When SportInno tournament `56878` goes live, the primary path takes over automatically.

### Manual scrape (CLI)

```bash
python -m scraper.run_once --time-window today_tomorrow --min-margin 1 --limit 10
```

Time windows:
- `today_tomorrow` — matches kicking off today or tomorrow (Europe/Sofia)
- `next_24h` — matches in the next 24 hours
- `all` — no kickoff filter (useful while testing World Cup fixtures)

**Note:** 8888 (SportInno) discovery may return partial results when their API blocks server-side calls. Other bookmakers work via plain HTTP.

### API

```bash
uvicorn api.main:app --reload --port 8000
```

Trigger scrape + get top 10 opportunities:

```bash
curl -X POST "http://localhost:8000/arbitrage/run?competition=world-cup-2026&time_window=today_tomorrow&min_margin=1&limit=10&seed=true"
```

Read last results without re-scraping:

```bash
curl "http://localhost:8000/arbitrage/opportunities?limit=10"
```

## Database

PostgreSQL database name: **arbitrage**

Schema: `sql/001_init.sql`

## Database tables

Created automatically by `init_db()` / `python -m scraper.db_init`:

| Table | Purpose |
|-------|---------|
| `bookmakers` | 6 sites + platform family |
| `market_types` | 1X2, O/U 2.5, corners 8.5/9.5 |
| `competitions` | e.g. `world-cup-2026` |
| `competition_sources` | Per-bookmaker discovery config (JSON) |
| `teams` / `matches` | Canonical fixtures + external IDs |
| `scrape_runs` | Each manual/API trigger |
| `odds_snapshots` | Raw odds per run |
| `arbitrage_opportunities` | Computed arbs per run |

Schema source: `sql/001_init.sql`

## Adding competitions later

Insert rows into `competitions` and `competition_sources` (tournament IDs per bookmaker). Same code path — no new application.

## Next steps

1. **React UI** — consume `GET /arbitrage/opportunities` and `POST /arbitrage/run`
2. **Cron** — schedule `POST /arbitrage/run` (e.g. every 30 min) once you are happy with accuracy
3. **European leagues** — add `competition_sources` rows for Premier League, La Liga, etc.
4. **Clean stale data** (optional, after matcher fixes):
   ```sql
   TRUNCATE arbitrage_opportunities, odds_snapshots, matches, teams RESTART IDENTITY CASCADE;
   ```
5. **Push to GitHub** — `git init && git remote add origin https://github.com/tdk928/arbitrage.git`

## GitHub

```bash
git init
git remote add origin https://github.com/tdk928/arbitrage.git
git add .
git commit -m "Initial arbitrage scraper MVP"
git push -u origin main
```
