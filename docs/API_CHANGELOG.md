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
| `feature/auth-login-register` | merged | `/auth/*` register, login, list users |
| `feature/auth-user-management` | merged | PATCH user, 24h activate, Postman, local DB setup |
| `fix/efbet-goals-hydration-market` | merged | Bugfix: Efbet O/U goals — без API промяна |
| `feature/admin-delete-arbitrage` | merged | `DELETE /arbitrage/v3/audit`, `DELETE /arbitrage/v3/top10/{rank}` |

---

> **Поддръжка:** Обновявай този файл преди всеки merge в `development` (нови/премахнати endpoints, UI бележки, bugfix-и).

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

> **Забележка:** `GET/POST /arbitrage/v3/rules*` endpoints са **премахнати** от публичното API. Seed остава само през CLI (`scripts/init_db.sh` / `scraper.seed_market_rules`).

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

### 10. Auth user management (`feature/auth-user-management`)

Admin endpoints за управление на потребители от UI + локална dev инфраструктура.

**Нови endpoints:**

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| `PATCH` | `/auth/users/{email}` | Admin Bearer | Partial update: `phone`, `valid_from`, `valid_to` |
| `POST` | `/auth/users/{email}/activate` | Admin Bearer | Бързо 24ч абонамент (без body) |

**Премахнати endpoints (не са публични):**

| Method | Path | Причина |
|--------|------|---------|
| `GET` | `/arbitrage/v3/rules` | Само internal/CLI seed |
| `GET` | `/arbitrage/v3/rules/{slug}/sites` | Само internal/CLI seed |
| `POST` | `/arbitrage/v3/rules/seed` | Само internal/CLI seed |

#### `PATCH /auth/users/{email}`

Partial update — изпращай само променените полета.

**Body (пример):**

```json
{
  "phone": "+359888123456",
  "valid_from": "2026-07-08T10:00:00.000Z",
  "valid_to": "2026-07-10T18:00:00.000Z"
}
```

**Response (200):** `UserListItem` (`email`, `phone`, `valid_from`, `valid_to`)

- API `valid_from` / `valid_to` ↔ DB `active_from` / `active_to`
- `400` — празен body или `valid_from > valid_to`
- `404` — потребителят не съществува

#### `POST /auth/users/{email}/activate`

Бързо активиране за 24 часа — за admin UI („Activate“ бутон).

- **Без request body**
- Задава `valid_from = now`, `valid_to = now + 24h` (UTC)
- **Response (200):** същият формат като PATCH

```bash
curl -X POST "http://localhost:8000/auth/users/user%40example.com/activate" \
  -H "Authorization: Bearer <admin_token>"
```

**Postman:** `postman/Arbitrage API.postman_collection.json` + `Arbitrage Local.postman_environment.json`

**Local Postgres:** `scripts/setup_postgres_user.sh` създава `arbitrage/arbitrage` user; `scripts/init_db.sh` го вика автоматично.

---

### 11. Efbet goals hydration market fix (`fix/efbet-goals-hydration-market`)

Bugfix в v3 market selection за Efbet `total_goals_ou` — hydration-break пазарът („Голове В Мача Преди Първа Пауза За Хидратация“) вече не се бърка с match total O/U.

- **Без API промяна** — само `match_criteria` в DB (`original_name_ends_with_line`)
- След deploy: `python -m scraper.seed_market_rules` + нов scrape

---

### 12. Admin delete arbitrage (`feature/admin-delete-arbitrage`)

Admin-only изтриване на фалшиви/грешни арбитражи от UI (напр. грешен market match с нереалистичен margin).

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| `DELETE` | `/arbitrage/v3/audit` | Admin Bearer | Изтрива 1 ред от `arbitrage_audit` |
| `DELETE` | `/arbitrage/v3/top10/{rank}` | Admin Bearer | Изтрива 1 ред от `arbitrage_top10_current` по PK `rank` |

Същият admin auth като `GET /auth/users` — `Authorization: Bearer <JWT>` с `role=admin` в payload.

#### `DELETE /arbitrage/v3/audit`

**Body (JSON):**

```json
{
  "run_id": 10,
  "rule_slug": "total_goals_ou",
  "home_team": "Spain",
  "away_team": "Belgium",
  "line": "0.5"
}
```

- Match по `scrape_run_id`, `rule_slug`, `home_team`, `away_team`, `line` (`null` и `""` се третират еднакво)
- `403` — не-admin; `401` — липсва/невалиден токен
- `404` — записът не съществува
- **Response:** `204 No Content` (алтернативно `200` с `{ "deleted": true }` — UI приема и двете)

```bash
curl -X DELETE "http://localhost:8000/arbitrage/v3/audit" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"run_id":10,"rule_slug":"total_goals_ou","home_team":"Spain","away_team":"Belgium","line":"0.5"}'
```

#### `DELETE /arbitrage/v3/top10/{rank}`

- `rank` — primary key в `arbitrage_top10_current` (обикновено 1–10)
- `403` / `401` — както audit
- `404` — rank не съществува
- **Response:** `204 No Content`

```bash
curl -X DELETE "http://localhost:8000/arbitrage/v3/top10/3" \
  -H "Authorization: Bearer <admin_token>"
```

#### `GET /arbitrage/v3/audit` — допълнение

Response обектите вече включват `event_key` (уникален ключ в `arbitrage_audit`) за по-надеждно delete в бъдеще:

```json
{
  "rank": 1,
  "event_key": "belgium|spain|2026-07-10T18:00:00+00:00|total_goals_ou|0.5",
  "run_id": 10,
  "rule_slug": "total_goals_ou",
  ...
}
```

CORS за `http://localhost:5173` вече покрива `DELETE` (глобално `allow_methods=["*"]` в `api/main.py`).

---

## Auth API (`/auth/*`)

CORS за `http://localhost:5173` е конфигуриран в `api/main.py`.

### Endpoints

| Method | Path | Auth | Описание |
|--------|------|------|----------|
| `POST` | `/auth/register` | — | Регистрация (email + password) |
| `POST` | `/auth/login` | — | Login (email + password) |
| `GET` | `/auth/users` | Admin Bearer | Списък всички потребители |
| `PATCH` | `/auth/users/{email}` | Admin Bearer | Partial update на потребител |
| `POST` | `/auth/users/{email}/activate` | Admin Bearer | 24ч абонамент (без body) |

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

### `PATCH /auth/users/{email}` (admin only)

Виж секция 10 по-горе.

### `POST /auth/users/{email}/activate` (admin only)

Виж секция 10 по-горе.

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
3. **Auth** — `register` / `login` + Bearer за admin views; `PATCH` за ръчно edit; `POST .../activate` за 24ч бутон.
4. **Admin delete** — `DELETE /arbitrage/v3/audit` (JSON body) и `DELETE /arbitrage/v3/top10/{rank}` за премахване на грешни арбитражи.
5. **v1/v2** — legacy; не ги ползвай за нов UI освен ако не е изрично нужно.

---

## Бърз smoke test

```bash
# Health
curl http://localhost:8000/health

# Top 10 (v3)
curl http://localhost:8000/arbitrage/v3/top10

# Audit (v3)
curl http://localhost:8000/arbitrage/v3/audit

# Auth
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'

# Activate user 24h (admin token)
curl -X POST "http://localhost:8000/auth/users/user%40example.com/activate" \
  -H "Authorization: Bearer <admin_token>"

# Delete audit entry (admin)
curl -X DELETE "http://localhost:8000/arbitrage/v3/audit" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"run_id":10,"rule_slug":"total_goals_ou","home_team":"Spain","away_team":"Belgium","line":"0.5"}'

# Delete top10 entry (admin)
curl -X DELETE "http://localhost:8000/arbitrage/v3/top10/3" \
  -H "Authorization: Bearer <admin_token>"
```
