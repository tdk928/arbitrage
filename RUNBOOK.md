# Arbitrage — Runbook

Daily commands and checks for the World Cup 2026 scraper MVP.

---

## 1. One-time setup

```bash
cd /Users/teodorkalev/Desktop/arbitrage
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Local Postgres (create DB once if needed)
createdb arbitrage

export DATABASE_URL="postgresql://teodorkalev@localhost:5432/arbitrage"

python -m scraper.db_init
python -m scraper.seed
```

Copy env template (optional):

```bash
cp .env.example .env
# Edit DATABASE_URL in .env if needed
```

---

## 2. Every session — activate environment

```bash
cd /Users/teodorkalev/Desktop/arbitrage
source .venv/bin/activate
export DATABASE_URL="postgresql://teodorkalev@localhost:5432/arbitrage"
```

Your prompt should show `(.venv)`.

---

## 3. Run scrape (CLI)

### Production window (matches today or tomorrow, Sofia time)

```bash
python -m scraper.run_once --time-window today_tomorrow --min-margin 1 --limit 10
```

Use this **from 11 June 2026 onward** when WC fixtures are actually today/tomorrow.

Until then, `opportunities: []` is **normal** — opener is 11 June, not today.

### All World Cup 2026 fixtures (recommended on `world-cup-future` branch)

Scrapes every WC match listed on all 6 bookmakers (Jun 11 – Jul 20), stores odds, computes arbitrage:

```bash
python -m scraper.run_world_cup --min-margin 1 --limit 10
```

Or via API:

```bash
curl -X POST "http://localhost:8000/arbitrage/world-cup/run?min_margin=1&limit=10"
```

Response includes `stats` with fixtures per bookmaker, matches linked, and coverage.

### Test all fixtures (no date filter)

```bash
python -m scraper.run_once --time-window all --min-margin 1 --limit 10
```

### Other options

```bash
# Next 24 hours only
python -m scraper.run_once --time-window next_24h --min-margin 1 --limit 10

# Show any arb (even tiny margins) for debugging
python -m scraper.run_once --time-window all --min-margin 0 --limit 10
```

---

## 4. What a good response looks like

```json
{
  "run_id": 9,
  "scraped_at": "2026-06-11T20:00:00+03:00",
  "time_window": "today_tomorrow",
  "competition": "world-cup-2026",
  "status": "success",
  "errors": null,
  "opportunities": [ ... ]
}
```

| Field | OK | Problem |
|-------|-----|---------|
| `status` | `"success"` | `"failed"` or `"partial"` → check `errors` |
| `errors` | `null` | Bookmaker scrape failures listed here |
| `opportunities` | Array (can be empty) | Empty on non-match days is expected |

---

## 5. Checks after a run

### 5.1 Quick sanity — Mexico opener (when in window)

After 11 June, first WC match should link **6 bookmakers**:

- efbet, winbet, inbet, palmsbet, 8888, bet365

### 5.2 Postgres — odds per bookmaker

```bash
psql arbitrage -c "
SELECT b.slug, COUNT(*) AS odds_rows
FROM odds_snapshots o
JOIN bookmakers b ON b.id = o.bookmaker_id
WHERE o.scrape_run_id = (SELECT MAX(id) FROM scrape_runs)
GROUP BY b.slug
ORDER BY b.slug;
"
```

Expect non-zero counts for all 6 when using `--time-window all`.

### 5.3 Postgres — latest opportunities

```bash
psql arbitrage -c "
SELECT t1.name || ' vs ' || t2.name AS match,
       mt.code AS market,
       ao.margin_pct,
       ao.bookmaker_count
FROM arbitrage_opportunities ao
JOIN matches m ON m.id = ao.match_id
JOIN teams t1 ON t1.id = m.home_team_id
JOIN teams t2 ON t2.id = m.away_team_id
JOIN market_types mt ON mt.id = ao.market_type_id
WHERE ao.scrape_run_id = (SELECT MAX(id) FROM scrape_runs)
ORDER BY ao.margin_pct DESC
LIMIT 10;
"
```

### 5.4 API (optional)

Terminal 1:

```bash
uvicorn api.main:app --reload --port 8000
```

Terminal 2:

```bash
curl http://localhost:8000/health

curl -X POST "http://localhost:8000/arbitrage/run?time_window=today_tomorrow&min_margin=1&limit=10"

curl "http://localhost:8000/arbitrage/opportunities?limit=10"
```

---

## 6. Re-seed config (after code/seed changes)

```bash
python -m scraper.seed
```

---

## 7. Clean stale matches (optional, once)

If you see wrong pairings like `Мексико vs Мексико` from early test runs:

```bash
psql arbitrage -c "
TRUNCATE arbitrage_opportunities, odds_snapshots, matches, teams
RESTART IDENTITY CASCADE;
"
python -m scraper.run_once --time-window all --min-margin 1 --limit 10
```

---

## 8. Bookmakers & platforms

| Site | Platform |
|------|----------|
| efbet | efbet API |
| winbet / inbet | EGT Digital |
| palmsbet | Altenar (`champ_id: 3146`) |
| bet365 | Hub HTML |
| 8888 | SportInno (`curl_cffi`) + Altenar fallback until WC live on SportInno |

---

## 9. Markets

- `MATCH_1X2` — 1 / X / 2
- `GOALS_OU_25` — Over/Under 2.5 goals
- `CORNERS_OU_85` / `CORNERS_OU_95` — corners

Arbitrage requires odds from **≥ 2 bookmakers** and `margin_pct >= min_margin` (default 1%).

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `command not found: python` | `source .venv/bin/activate` or use `.venv/bin/python` |
| `role "arbitrage" does not exist` | Set `DATABASE_URL` with your macOS user (see section 1) |
| `opportunities: []` before 11 Jun | Use `--time-window all` or wait until match day |
| 8888 returns 0 fixtures | Re-run after WC is on SportInno; fallback uses Altenar until then |
| Postgres connection refused | Start Postgres: `brew services start postgresql` |

---

## 11. Project layout

```
arbitrage/
├── api/              # FastAPI (POST /arbitrage/run)
├── scraper/          # Scrapers, matcher, arbitrage engine
├── sql/001_init.sql  # Schema reference
├── RUNBOOK.md        # This file
└── README.md         # Architecture overview
```
