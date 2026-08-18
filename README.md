# Podium — Fitness Challenge Application

Podium is a fitness activity scoring application where users log physical activities, receive points according to defined scoring rules, view their personal performance dashboard, and compare their score on a public global leaderboard.

## Core Features

- **User Registration & Login** — name-based identification with JWT session tokens (no password required)
- **Six Activity Types** — Running, Walking, Cycling, Swimming, Gym, Daily Steps
- **Server-Side Scoring** — all point calculations happen on the backend; the frontend never computes authoritative points
- **Daily Steps Replacement** — submitting a new step count replaces (not accumulates) the existing daily total
- **Personal Dashboard** — total points, sport breakdown, points-over-time chart, recent activity history
- **Public Global Leaderboard** — live ranking with rank trend based on daily snapshots
- **Daily Leaderboard Snapshots** — generated at midnight IST via APScheduler + CLI manual trigger
- **Help Page** — explains scoring rules, activity types, and system behaviour
- **Logout / Switch User** — clears client-side token and returns to login

### Activity Logging UX

- Distance sports (Running, Walking, Cycling): distance in km
- Duration sports (Swimming, Gym): human-friendly Hours + Minutes input
- Daily Steps: cumulative step count for the day
- Server generates `recordedAt` timestamp (UTC); derives `activity_date` (IST calendar date)

---

## Scoring Rules

All scoring is performed server-side by `backend/app/services/scoring.py`. Points are always integer-floored (never rounded up).

| Sport | Metric | Rate | Formula |
|-------|--------|------|---------|
| Running | km | 100 pts/km | `floor(km × 100)` |
| Walking | km | 50 pts/km | `floor(km × 50)` |
| Cycling | km | 25 pts/km | `floor(km × 25)` |
| Swimming | seconds | 15 pts/min | `floor(sec ÷ 60) × 15` |
| Gym | seconds | 5 pts/min | `floor(sec ÷ 60) × 5` |
| Daily Steps | count | 1 pt/100 steps | `floor(stepCount ÷ 100)` |

For duration sports, only complete minutes count — partial minutes are floored before multiplying by the rate.

---

## Architecture

```
┌─────────────┐       HTTP/JSON        ┌────────────────────┐       SQL        ┌──────────┐
│  React SPA  │ ─────────────────────▶ │     FastAPI        │ ───────────────▶ │  SQLite  │
│  (Vite)     │ ◀───────────────────── │  routers→services→ │ ◀─────────────── │          │
└─────────────┘   Bearer token auth    │  db (SQLAlchemy)   │                  └──────────┘
                                       └────────────────────┘
                                              ↑
                                       ┌──────┴──────┐
                                       │ APScheduler │  00:00 IST daily
                                       │ + CLI entry │  snapshot generation
                                       └─────────────┘
```

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + React Router + Recharts |
| Backend | Python + FastAPI + Uvicorn |
| Database | SQLite (via SQLAlchemy ORM) |
| Auth | JWT (HS256) via python-jose — session-token identification, not credential-based |
| Scheduling | APScheduler (BackgroundScheduler, CronTrigger at 00:00 IST) |
| Linting | Ruff (backend), ESLint (frontend) |
| Testing | pytest (backend), Vitest + Testing Library (frontend) |

### Data Flows

**Activity ingestion**: User → React form → `POST /api/activities` (Bearer token) → token middleware resolves userId → validate sport/metric → server generates `recorded_at` (UTC) and derives `activity_date` (IST) → `compute_points()` → persist → response with points.

**Leaderboard**: `GET /api/leaderboard` (public) → live `SUM(points) GROUP BY user_id` → tie-break ordering → rank-trend from most recent snapshot → response.

**Dashboard**: `GET /api/users/{id}/dashboard` (Bearer, self-only) → aggregate activityHistory (recorded_at DESC), volumeOverTime (activity_date ASC, sparse), sportBreakdown → response.

**Snapshot**: APScheduler at 00:00 IST (or CLI `python -m app.jobs`) → `generate_daily_snapshot(target_date=yesterday)` → aggregate leaderboard for activities with `activity_date ≤ target_date` → assign ranks → persist snapshot + entries.

---

## Project Structure

```
ngov/
├── backend/
│   ├── app/
│   │   ├── config.py              # pydantic-settings configuration
│   │   ├── main.py                # FastAPI app factory + lifespan
│   │   ├── dependencies.py        # Bearer token dependency
│   │   ├── db/
│   │   │   ├── database.py        # SQLAlchemy engine + session
│   │   │   ├── models.py          # ORM models (User, Activity, Snapshots)
│   │   │   └── init_db.py         # create_all on startup
│   │   ├── routers/
│   │   │   ├── auth.py            # /api/auth/register, /api/auth/login
│   │   │   ├── activities.py      # POST /api/activities
│   │   │   ├── leaderboard.py     # GET /api/leaderboard
│   │   │   └── dashboard.py       # GET /api/users/{id}/dashboard
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── scoring.py         # Pure scoring engine (no DB/HTTP)
│   │   │   ├── activity_service.py
│   │   │   ├── auth_service.py
│   │   │   ├── leaderboard_service.py
│   │   │   ├── dashboard_service.py
│   │   │   └── snapshot_service.py
│   │   └── jobs/
│   │       ├── scheduler.py       # APScheduler setup
│   │       └── __main__.py        # CLI snapshot trigger
│   ├── tests/
│   │   ├── unit/                  # Scoring, ranking, scheduler, snapshot date
│   │   └── integration/           # Auth, activities, dashboard, leaderboard, snapshot, concurrency
│   ├── requirements.txt
│   ├── ruff.toml
│   ├── pytest.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Router + auth guards
│   │   ├── main.jsx               # React root
│   │   ├── api/client.js          # Fetch wrapper with token attachment
│   │   ├── context/AuthContext.jsx
│   │   ├── components/            # Header, ScoreDisplay
│   │   ├── pages/                 # Register, Login, Dashboard, LogActivity, Leaderboard, Help
│   │   ├── styles/                # Global CSS + design tokens
│   │   └── utils/                 # Display formatting helpers
│   ├── tests/                     # Vitest + Testing Library tests
│   ├── vite.config.js
│   └── package.json
├── AGENTS.md                      # Engineering rules
├── SRS.md                         # Software Requirements Specification
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from the example
copy .env.example .env
# Edit .env — set a real JWT_SECRET for any non-local use

# Start the backend (creates the SQLite DB on first run)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server (proxies /api to localhost:8000)
npm run dev
```

The frontend dev server runs on `http://localhost:5173` by default. API requests are proxied to the backend at `http://localhost:8000`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `fitness.db` | Path to the SQLite database file |
| `JWT_SECRET` | `change-me-before-use` | HS256 signing key for session tokens |
| `JWT_EXPIRE_HOURS` | `24` | Token lifetime in hours |
| `TIMEZONE` | `Asia/Kolkata` | Canonical business timezone (do not change) |

---

## Testing

### Backend Tests

```bash
cd backend
pytest
```

Test coverage includes:
- **Unit tests**: scoring engine (all sports, flooring boundaries, zero values), ranking/tie-break, scheduler target date computation, snapshot date validation
- **Integration tests**: auth (register, login, duplicate, token verification), activities (all 6 sports, validation, daily steps upsert/concurrency), dashboard (aggregation, ownership), leaderboard (ordering, rank trend), snapshot generation (idempotency, date filtering), concurrent registration

### Backend Linting

```bash
cd backend
ruff check .
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Frontend Production Build

```bash
cd frontend
npm run build
```

---

## API Overview

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | Public | Register a new user, receive token |
| POST | `/api/auth/login` | Public | Login existing user, receive fresh token |
| POST | `/api/activities` | Bearer | Log an activity or upsert daily steps |
| GET | `/api/leaderboard` | Public | Live ranked leaderboard with rank trend |
| GET | `/api/users/{id}/dashboard` | Bearer (self) | Personal stats and history |

### `POST /api/auth/register`

```json
Request:  { "firstName": "Ada", "lastName": "Lovelace" }
201:      { "userId": 1, "firstName": "Ada", "lastName": "Lovelace", "token": "<jwt>" }
409:      { "error": "USER_ALREADY_EXISTS", "message": "..." }
400:      { "error": "VALIDATION_ERROR", "message": "..." }
```

### `POST /api/auth/login`

```json
Request:  { "firstName": "Ada", "lastName": "Lovelace" }
200:      { "userId": 1, "firstName": "Ada", "lastName": "Lovelace", "token": "<jwt>" }
404:      { "error": "USER_NOT_FOUND", "message": "..." }
```

### `POST /api/activities`

userId derived from the Bearer token — never from the request body. `recordedAt` is server-generated.

```json
Request (distance):  { "sportType": "running", "distanceKm": 5.3 }
Request (duration):  { "sportType": "swimming", "durationSec": 1855 }
Request (steps):     { "sportType": "daily_steps", "stepCount": 8342 }

201 (new):    { "activityId": 10, "sportType": "running", "points": 530, "recordedAt": "2026-08-13T01:30:00Z" }
200 (upsert): { "activityId": 10, "sportType": "daily_steps", "points": 83, "recordedAt": "...", "updated": true }
400:          { "error": "VALIDATION_ERROR", "message": "..." }
401:          { "error": "UNAUTHORIZED", "message": "Missing or invalid session token." }
```

### `GET /api/leaderboard`

```json
200: [
  { "rank": 1, "userId": 2, "name": "Snegith V", "totalPoints": 4800, "rankTrend": 2 },
  { "rank": 2, "userId": 1, "name": "Ada Lovelace", "totalPoints": 4500, "rankTrend": -1 },
  { "rank": 3, "userId": 3, "name": "Grace Hopper", "totalPoints": 4500, "rankTrend": null }
]
```

`rankTrend = previousSnapshotRank − currentLiveRank` (positive = improved, null = no prior snapshot).

### `GET /api/users/{id}/dashboard`

Token's userId must equal path `{id}`, otherwise 403.

```json
200: {
  "totalPoints": 4210,
  "activityHistory": [{ "activityId": 10, "sportType": "running", "points": 530, "recordedAt": "..." }],
  "volumeOverTime": [{ "date": "2026-08-13", "points": 210 }],
  "sportBreakdown": { "running": 2100, "gym": 1200 }
}
403: { "error": "FORBIDDEN", "message": "Cannot access another user's dashboard." }
401: { "error": "UNAUTHORIZED", "message": "Missing or invalid session token." }
```

---

## Timezone Behaviour

- Canonical timezone: **Asia/Kolkata (IST, UTC+05:30)**
- `recorded_at` — server-generated UTC instant (ISO 8601, `Z` suffix)
- `activity_date` — IST calendar date (`YYYY-MM-DD`), derived in Python (`zoneinfo.ZoneInfo("Asia/Kolkata")`) at write time
- `volumeOverTime` — grouped by stored `activity_date` (IST days), not recomputed from UTC at query time
- Snapshot boundaries — based on IST calendar days; the 00:00 IST job snapshots the previous day
- Daily Steps uniqueness — one record per `(user_id, activity_date)` where `activity_date` is the IST date

---

## Manual Snapshot Generation

```bash
cd backend

# Generate snapshot for yesterday (default)
python -m app.jobs

# Generate snapshot for a specific past date
python -m app.jobs --date 2026-08-13
```

The CLI calls the same `generate_daily_snapshot()` function used by the scheduler. No HTTP endpoint exists for snapshot generation.

---

## Design Notes

- The leaderboard includes all registered users (including those with zero activities) via LEFT JOIN / COALESCE behaviour
- Activity history is ordered by `recorded_at` descending (most recent first)
- Volume over time is ordered by `activity_date` ascending and is sparse (only dates with activity are included)
- Rank trend uses the most recent snapshot only — intra-day rank changes are not individually tracked
- The frontend displays the 20 most recent activities in the dashboard history section
- Session tokens are stateless JWTs (no server-side session table); expiry is 24 hours
