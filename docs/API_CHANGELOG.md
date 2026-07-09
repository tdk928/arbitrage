# API Changelog & UI Integration Guide

Документ за синхронизация на frontend с backend API. Използвай го в нов Cursor чат:

> Прочети `docs/API_CHANGELOG.md` и синхронизирай UI с актуалните endpoints.

**Base URL (local):** `http://localhost:8000`  
**OpenAPI / Swagger:** `http://localhost:8000/docs`  
**Препоръчителна версия за UI:** **v3** (`/arbitrage/v3/*`)

---

## Статус по branch

| Branch | Статус в `development` | Какво добавя |
|--------|------------------------|--------------|
| `world-cup-future` | merged | MVP scraper + v1 API |
| `fix/efbet-1x2-draw-odds` | merged | Bugfix в scraper (без нови endpoints) |
| v2 pipeline | merged | `/arbitrage/v2/*` |
| `feature/market-rules-v3` | merged | v3 rules pipeline + DB migrations |
| `feature/v3-event-fetch-cache` | merged | Backend cache (без API промяна) |
| `feature/v3-scrape-api` | merged | `POST /arbitrage/v3/run`, `GET /top10` |
| `refactor/audit-table-top20` | merged | `GET /arbitrage/v3/audit` |
| `feature/auth-login-register` | **не е merge-нат** | `/auth/*` — виж секция „Pending“ |

---

## PR / feature история (merge-нато в `development`)

### 1. World Cup MVP (`world-cup-future`)

Първоначален arbitrage scraper за World Cup 2026 и v1 REST API.

**Endpoints (v1 — legacy):**

| Method | Path | Описание |
|--------|------|----------|
| `GET` | `/health` | Health check |
| `POST` | `/arbitrage/run` | Scrape + arbitrage (v1 pipeline) |
| `POST` | `/arbitrage/world-cup/run` | World Cup scrape (6 bookmakers) |
| `GET` | `/arbitrage/opportunities` | Arbitrage bets от последен scrape |
| `GET` | `/arbitrage/board` | Debug: raw odds grid |

**Query params (`POST /arbitrage/run`):**

- `competition` — default `world-cup-2026`
- `time_window` — `next_24h` \| `today_tomorrow` \| `all` \| `world_cup`
- `min_margin` — default `1.0`
- `limit` — default `10` (1–100)
- `budget` — default `100.0` EUR
- `seed` — default `false`

---

### 2. efbet 1X2 fix (`fix/efbet-1x2-draw-odds`)

Поправка на парсване на draw odds при efbet. **Няма нови API endpoints.**

---

### 3. v2 all-markets pipeline

Нов pipeline за EGT, Altenar, efbet с отделни v2 таблици.

**Endpoints (v2 — legacy):**

| Method | Path | Описание |
|--------|------|----------|
| `POST` | `/arbitrage/v2/run` | Scrape + arbitrage (v2) |
| `POST` | `/arbitrage/v2/world-cup/run` | World Cup v2 scrape |
| `GET` | `/arbitrage/v2/opportunities` | Arbitrage bets от v2 scrape |
| `GET` | `/arbitrage/v2/markets` | Debug: raw/cross-bookmaker markets |

Query params — аналогични на v1 (`competition`, `time_window`, `min_margin`, `limit`, `budget`, `seed`).

---

### 4. Market Rules v3 (`feature/market-rules-v3`)

Rule-based pipeline с Flyway migrations, market rules в Postgres, arbitrage по curated rules.

**DB migrations:** `V001`–`V004`  
**Market rules:** `total_goals_ou`, `both_teams_to_score`, `match_result_1x2`, `total_corners_ou`, `total_cards_ou`, `first_half_total_goals_ou`  
**Детайли:** `docs/MARKET_RULES_V3.md`

**Нови endpoints:**

| Method | Path | Описание |
|--------|------|----------|
| `GET` | `/arbitrage/v3/rules` | Списък активни rules |
| `GET` | `/arbitrage/v3/rules/{slug}/sites` | Bookmaker mapping за rule |
| `POST` | `/arbitrage/v3/rules/seed` | Seed rules в DB |

**`GET /arbitrage/v3/rules` query:**

- `slug` (optional) — филтър по rule slug

**Response пример (`GET /rules`):**

```json
{
  "count": 6,
  "rules": [
    {
      "id": 1,
      "slug": "total_goals_ou",
      "label": "Over/Under Total Goals",
      "description": "...",
      "outcome_roles": ["over", "under"],
      "scope": "match",
      "line_filter": "half_lines",
      "is_active": true,
      "site_matches": [...]
    }
  ]
}
```

---

### 5. v3 event fetch cache (`feature/v3-event-fetch-cache`)

Кешира per-event market HTTP заявки в v3 pipeline. **Без API промяна** — само performance.

---

### 6. v3 scrape API (`feature/v3-scrape-api`)

Тригер на v3 scrape през API + четене на top 10 snapshot.

| Method | Path | Описание |
|--------|------|----------|
| `POST` | `/arbitrage/v3/run` | Стартира v3 scrape + arbitrage |
| `GET` | `/arbitrage/v3/top10` | Текущ top-10 snapshot (без re-scrape) |

**`POST /arbitrage/v3/run` query params:**

| Param | Default | Описание |
|-------|---------|----------|
| `competition` | `world-cup-2026` | Competition slug |
| `time_window` | `world_cup` | `next_24h` \| `today_tomorrow` \| `all` \| `world_cup` |
| `min_margin` | `1.0` | Минимален ROI% |
| `limit` | `10` | Top N (1–100) |
| `rules` | `null` | Optional list of rule slugs |

**`GET /arbitrage/v3/top10` response** — масив от обекти:

```json
[
  {
    "rank": 1,
    "run_id": 6,
    "rule_slug": "total_goals_ou",
    "match": "France vs Morocco",
    "home_team": "France",
    "away_team": "Morocco",
    "market": "Over/Under Total Goals (match) 1.5",
    "line": "1.5",
    "margin_pct": 4.66,
    "implied_total": 0.9555,
    "bookmaker_count": 2,
    "kickoff_utc": "2026-07-10T18:00:00+00:00",
    "captured_at": "2026-07-08T09:00:00+00:00",
    "legs": [
      {"role": "over", "bookmaker": "betano", "odd": 1.34},
      {"role": "under", "bookmaker": "efbet", "odd": 4.78}
    ]
  }
]
```

---

### 7. Audit top-20 (`refactor/audit-table-top20`)

Rolling audit таблица — top 20 уникални събития по margin.

| Method | Path | Описание |
|--------|------|----------|
| `GET` | `/arbitrage/v3/audit` | Top 20 audit записи (без re-scrape) |

**Response** — масив, същата структура като `top10` + `scrape_date`, `scrape_time`.

---

### 8. Restore v1 models

Възстановени SQLAlchemy v1 модели. **Без API промяна.**

---

### 9. pytest regression suite

Тестове за v3 business logic. **Без API промяна.**

---

## Pending: Auth API (`feature/auth-login-register`)

> **Не е merge-нат в `development` към момента на този документ.**  
> Branch: `feature/auth-login-register`  
> След merge добави CORS + auth router в `api/main.py`.

### Endpoints

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| `POST` | `/auth/register` | — | Регистрация (email + password) |
| `POST` | `/auth/login` | — | Login (email + password) |
| `GET` | `/auth/users` | Admin Bearer | Списък всички потребители |

### `POST /auth/register`

**Body:**

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

- `password` — min 8 символа
- По подразбиране роля: `client`

**Response (201):**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### `POST /auth/login`

**Body:**

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

**Response (200):** същият формат като register.

**Грешки:** `401` — invalid credentials; `409` (register) — email вече съществува.

### JWT payload (decode на frontend)

```json
{
  "sub": "1",
  "email": "user@example.com",
  "role": "client",
  "has_active_subscription": false,
  "iat": 1783624040,
  "exp": 1783627640
}
```

| Claim | Описание |
|-------|----------|
| `role` | `client` или `admin` |
| `has_active_subscription` | `true` ако `now` е между `active_from` и `active_to` в DB |
| `exp` | Token expiry (unix timestamp) |

**Роли:**

| Роля | Къде | Описание |
|------|------|----------|
| `anonymous` | Frontend only | Default без валиден токен |
| `client` | DB + JWT | Обикновен потребител |
| `admin` | DB + JWT | Admin достъп |

### `GET /auth/users` (admin only)

**Header:**

```
Authorization: Bearer <admin_access_token>
```

**Response (200):**

```json
{
  "count": 1,
  "users": [
    {
      "email": "user@example.com",
      "phone": null,
      "valid_from": null,
      "valid_to": null
    }
  ]
}
```

- Връща **всички** потребители (без филтър по subscription)
- `valid_from` / `valid_to` ← `active_from` / `active_to` в DB
- `403` — не-admin; `401` — липсва/невалиден токен

### DB tables (auth migrations)

- `V007` — `roles` (`client`, `admin`), `users` (`email`, `password_hash`, `role_id`, `registered_at`, `active_from`, `active_to`)
- `V008` — `users.phone`

### Frontend scaffold (auth branch)

```
frontend/src/auth/
  api.ts          — register/login fetch
  token.ts        — parse JWT, expiry check, localStorage
  AuthContext.tsx — session state, anonymous default
  types.ts        — TypeScript types
```

**Env:**

- Backend: `JWT_SECRET`, `JWT_EXPIRE_MINUTES` (виж `.env.example`)
- Frontend: `VITE_API_BASE_URL=http://localhost:8000`

---

## Препоръки за UI

1. **Arbitrage данни** — ползвай **v3**: `GET /arbitrage/v3/top10` и `GET /arbitrage/v3/audit`.
2. **Scrape trigger** — `POST /arbitrage/v3/run` (бавна операция; покажи loading).
3. **Auth** — след merge на auth branch: `frontend/src/auth/` + Bearer header за admin views.
4. **v1/v2** — legacy; не ги ползвай за нов UI освен ако не е изрично нужно.

---

## Бърз smoke test

```bash
# Health
curl http://localhost:8000/health

# Top 10 (v3)
curl http://localhost:8000/arbitrage/v3/top10

# Audit (v3)
curl http://localhost:8000/arbitrage/v3/audit

# Auth (след merge на auth branch)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'
```
