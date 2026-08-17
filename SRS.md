# Fitness Challenge Application — Software Requirements Specification (Final)

**Stack**: React (Vite) · FastAPI · SQLite
**Status**: Finalized — ready for implementation

## Revision History

| Version | Date | Change |
|---|---|---|
| v1.0 | Draft | Initial SRS: registration, activity ingestion, scoring, live leaderboard, dashboard |
| v1.1 | Post client Q&A | Added ranking-trend via daily snapshots, daily-steps upsert semantics, tie-break rule, timezone convention |
| v2.0 | Final | Added optional basic session-token identification, login endpoint, token-derived identity on protected endpoints, IST timezone finalized |
| v2.1 | Final | Snapshot semantics corrected (represents the completed previous day); timestamp storage convention fixed (UTC storage, IST business-date computation, no more "confirm during implementation"); `recordedAt` is now server-generated only; daily-steps uniqueness moved to an explicit `activity_date` column |
| v2.2 (this doc) | Post-implementation | Documentation pass: explicit `activityHistory` ordering (recorded_at DESC), `volumeOverTime` ordering (activity_date ASC, sparse), leaderboard zero-activity user inclusion, daily-steps replacement semantics clarified, frontend requirements added (§14) |

---

## 1. Introduction

### 1.1 Purpose
Specifies the functional and non-functional requirements for the Fitness Challenge Application: a system that ingests fitness activity data across multiple sports, normalizes it into a unified points system, and surfaces it via a live global leaderboard (with day-over-day rank trend) and a personal dashboard.

### 1.2 Scope
**In scope**: user registration, basic session-token identification (optional/bonus, not credential-based auth), activity ingestion, scoring/normalization, live leaderboard with rank trend, daily leaderboard snapshotting, personal dashboard, supporting REST API and persistence layer.
**Out of scope**: password/credential-based authentication, social features (friends, direct challenges), mobile apps, third-party fitness-device integration, leaderboard pagination.

### 1.3 Definitions
- **Points**: normalized score derived from a raw activity metric via the conversion table in §9.
- **Activity**: one logged instance of a sport with a raw metric (distance/duration/count).
- **Leaderboard**: live, rank-ordered list of users by total accumulated points.
- **Snapshot**: a stored copy of the leaderboard's final ranks for a **completed** IST calendar day, generated at 00:00 IST (i.e. the snapshot generated at midnight represents *yesterday*, not the day just starting). Used only as the historical baseline for rank trend.
- **Activity date**: the IST calendar date (`YYYY-MM-DD`) an activity is attributed to, computed by the backend from the server-generated UTC timestamp at write time. Stored explicitly (see §7), not derived via SQL expression at query time.
- **Session token**: an opaque/signed identifier issued at registration or login that maps to a `userId` on subsequent requests. Explicitly **not** credential-based authentication — see §2.3.

---

## 2. Overall Description

### 2.1 Product Perspective
Standalone three-tier web application: React SPA client, FastAPI REST backend, SQLite persistence. No external system dependencies.

### 2.2 User Classes
Single user class. Every registered user can log activities, view the (public) leaderboard, and view their own dashboard.

### 2.3 Assumptions & Constraints
- **Session-based identification, not authentication.** The system issues a signed session token (JWT) after registration or login. The token identifies the registered user for subsequent API requests. **No password or credential is verified at any point** — anyone who submits a matching first/last name can obtain a valid token for that identity. This was explicitly confirmed as optional/bonus scope by the client, implemented at "basic" level by design, and is documented here so it is not mistaken for security-grade authentication.
- Duplicate-user detection remains name-only (first + last name, normalized), per the original spec — a real limitation, not resolved by adding session tokens.
- Relational/in-memory DB per the assignment brief → SQLite chosen.
- Single-server deployment; no horizontal-scaling requirement stated.
- Canonical timezone is `Asia/Kolkata` (IST, UTC+05:30) for all date-bucketed *business logic* — see §9.1. **Storage convention (fixed, not to be revisited during implementation)**: all timestamps are stored in UTC (`recorded_at`, `created_at`, all `TEXT` datetime columns); every date-bucketing decision (daily-steps `activity_date`, `volumeOverTime` buckets, snapshot day boundary) is computed by the **backend application layer** converting UTC → IST using a proper timezone library (Python `zoneinfo`), never via ad hoc SQL offset arithmetic.
- `recordedAt` is **always server-generated**, never client-supplied — see §8. This removes both client/server timezone-interpretation ambiguity and the ability to backdate or postdate an activity.

---

## 3. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | System shall allow registering a user via first name + last name. |
| FR-2 | System shall reject registration if a user with the same first+last name (case/whitespace-insensitive) already exists. |
| FR-3 | System shall return a unique `userId` and a session token on successful registration. |
| FR-4 | System shall allow an existing user to obtain a fresh session token via login (first + last name lookup). |
| FR-5 | System shall require a valid session token on all activity-ingestion and personal-dashboard requests, and shall derive `userId` from the token — never from a client-supplied body field. |
| FR-6 | System shall accept activity submissions for running, walking, cycling (distance); gym, swimming (duration); daily steps (count). |
| FR-7 | System shall reject an activity submission with `400` if the sport/metric pairing is invalid or the payload is malformed. |
| FR-8 | System shall compute points for every accepted activity per the conversion table in §9, applying the specified flooring rule. |
| FR-9 | System shall persist computed points alongside the raw activity data. |
| FR-10 | For `daily_steps`, if a record already exists for the authenticated user on the current IST calendar date, the system shall **replace** (not accumulate) that record's step count with the new value and recompute its points, rather than inserting a new row. The client submits the cumulative daily total from their device. |
| FR-11 | System shall expose a live global leaderboard ranked by total accumulated points, descending, with deterministic tie-breaking (§9.2). The leaderboard includes all registered users, including those with zero activities (displayed with `totalPoints: 0`). |
| FR-12 | System shall generate a leaderboard snapshot at 00:00 IST, storing each user's rank and total points for the **completed previous IST calendar day** (i.e. the 00:00 IST run on Aug 14 produces the Aug 13 snapshot). |
| FR-13 | System shall include a `rankTrend` value on each leaderboard entry, computed as `previousRank − currentRank` against the most recent prior snapshot; `null` if no prior snapshot exists for that user. |
| FR-14 | System shall expose a per-user dashboard showing activity history (ordered by `recorded_at` descending), point volume over time (ordered by `activity_date` ascending, sparse — only dates with activity), and a breakdown of points by sport. |
| FR-15 | System shall reject activity submissions from a token whose `userId` does not resolve to an existing user, or dashboard requests for a `userId` that does not match the authenticated token's `userId`. |
| FR-16 | System shall provide a manually-triggerable snapshot generation path (CLI command), calling the identical function used by the scheduled job, for testing/demo purposes. |

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Correctness over caching** — the leaderboard is always computed live from current activity data; only rank-trend comparison uses stored history. |
| NFR-2 | **Consistency** — duplicate-user prevention holds under concurrent registration requests (DB constraint, not just app-level check). |
| NFR-3 | **Responsiveness** — frontend usable on both desktop and mobile viewport widths. |
| NFR-4 | **Testability** — scoring logic is a pure function, independently unit-testable without HTTP/DB. |
| NFR-5 | **Auditability** — every non-steps activity retains its raw input alongside computed points; steps activity retains the current cumulative daily value with points always in sync with it. |
| NFR-6 | **Honest security posture** — session-token identification is documented as such, not oversold as authentication, anywhere it appears in code comments, API docs, or this SRS. |
| NFR-7 | **Operational simplicity** — the snapshot job and its manual/CLI trigger share one implementation; no divergent "demo mode" logic path. |
| NFR-8 | **Timezone consistency** — every date-bucketing operation (steps upsert, `volumeOverTime`, snapshot generation) uses IST uniformly; no operation may use UTC or server-local time instead. |

---

## 5. System Features (User Stories + Acceptance Criteria)

**US-1 — Registration**
- Given valid first/last name, when submitted, then `201` is returned with a unique `userId` and a session token.
- Given a name matching an existing user (case/whitespace-insensitive), when submitted, then `409 USER_ALREADY_EXISTS` is returned and no new row is created.
- Given an empty or missing first/last name, when submitted, then `400 VALIDATION_ERROR` is returned.

**US-2 — Login (returning user)**
- Given a first/last name matching an existing user, when submitted to login, then `200` is returned with that user's `userId` and a freshly issued token.
- Given a first/last name matching no existing user, when submitted to login, then `404 USER_NOT_FOUND` is returned.

**US-3 — Distance activity (running/walking/cycling)**
- Given a valid token and `distanceKm > 0` for a distance sport, when submitted, then points are computed per §9.1 and `201` is returned with the correctly floored value.
- Given `durationSec` or `stepCount` present alongside a distance sport, when submitted, then `400` is returned.
- Given a missing or invalid token, when submitted, then `401 UNAUTHORIZED` is returned.

**US-4 — Duration activity (gym/swimming)**
- Given a valid token and `durationSec` for gym/swimming, when submitted, then points are computed using floored-to-minute logic and `201` is returned.
- Given `distanceKm` or `stepCount` present alongside a duration sport, when submitted, then `400` is returned.
- Given `durationSec` under 60 (e.g. 55s), when submitted, then 0 minutes are counted and points reflect that.

**US-5 — Daily steps**
- Given a valid token and no existing record for the current IST date, when a step count is submitted, then a new activity is created with `floor(stepCount / 100)` points.
- Given a valid token and an existing record for the current IST date, when a new step count is submitted, then the existing record's `step_count` and `points` are **updated in place** (not a new row).
- Given `distanceKm` or `durationSec` present alongside `daily_steps`, when submitted, then `400` is returned.

**US-6 — Leaderboard**
- Given multiple users with activities, when the leaderboard is fetched, then users are returned ordered by `totalPoints` descending, ties broken by `created_at` ascending then `userId` ascending.
- Given a user with a prior day's snapshot, when the leaderboard is fetched, then `rankTrend` reflects `previousRank − currentRank`.
- Given a user with no prior snapshot (e.g. registered today), when the leaderboard is fetched, then `rankTrend` is `null`.
- Given no registered users, when the leaderboard is fetched, then an empty array is returned with `200`.
- The leaderboard endpoint requires no authentication (public read).

**US-7 — Dashboard**
- Given a valid token, when the authenticated user's own dashboard is fetched, then `200` is returned with `totalPoints` equal to the sum of all their activity points, and `sportBreakdown` values summing to `totalPoints`.
- Given a valid token but a requested `userId` that does not match the token's `userId`, when the dashboard is fetched, then `403 FORBIDDEN` is returned.
- Given a valid user with zero activities, when the dashboard is fetched, then `200` is returned with `totalPoints: 0`, empty arrays, and an empty `sportBreakdown` object.
- Given a missing or invalid token, when the dashboard is fetched, then `401 UNAUTHORIZED` is returned.

**US-8 — Invalid-input feedback**
- Given any malformed or sport/metric-mismatched activity payload, when submitted, then the `400` response's `message` names the specific field/rule violated.

**US-9 — Daily snapshot generation**
- At 00:00 IST, the system shall compute and persist the leaderboard snapshot for the **just-completed** IST calendar day (not the day about to start) exactly once.
- Given the CLI trigger is invoked manually, then the identical snapshot-generation logic runs and produces the same result as the scheduled job would, for the same target date (the most recently completed day).
- Given a snapshot already exists for its target date, when generation runs again, then it does not create a duplicate (`UNIQUE(snapshot_date)` enforced).

---

## 6. System Architecture

```
┌─────────────┐        HTTPS/JSON        ┌────────────────────────┐        SQL        ┌──────────┐
│   React SPA │ ───────────────────────▶ │        FastAPI          │ ────────────────▶ │  SQLite  │
│             │ ◀─────────────────────── │  routers → services →   │ ◀──────────────── │   file   │
│ • Register  │   Authorization: Bearer  │  db                     │      rows          └──────────┘
│ • Login     │                          │                          │
│ • Log Activity│                        │  ┌────────────────────┐ │        ┌──────────────────────┐
│ • Leaderboard │                        │  │ Token middleware    │ │        │  APScheduler         │
│ • Dashboard   │                        │  ├────────────────────┤ │        │  00:00 IST daily      │
└─────────────┘                          │  │ Validation           │ │  ───▶  │  generate_daily_      │
                                          │  ├────────────────────┤ │        │  snapshot()            │
                                          │  │ Scoring engine       │ │        └───────────┬───────────┘
                                          │  ├────────────────────┤ │                    also callable via
                                          │  │ Leaderboard engine   │ │                    CLI (same function)
                                          │  └────────────────────┘ │
                                          └────────────────────────┘
```

- **Frontend (React/Vite)**: talks to backend only via REST/JSON; stores the session token client-side and attaches it as `Authorization: Bearer <token>` on protected requests; checks for an existing stored token on load to skip straight to Dashboard, with an explicit "switch user" action to clear it.
- **Backend (FastAPI)**: layered `routers/ → services/ → db/`. `services/scoring.py` is pure and has zero HTTP/DB coupling (NFR-4). Token verification is a FastAPI dependency applied to protected routes only (activity ingestion, dashboard) — leaderboard and registration/login remain public.
- **Scheduler**: APScheduler running in-process, triggers `generate_daily_snapshot()` at 00:00 IST. A CLI entry point (`python -m app.jobs.snapshot`) calls the same function for manual/demo use — no HTTP endpoint is exposed for this, to avoid an unauthenticated write surface (§13, R9).
- **Database (SQLite via SQLAlchemy/sqlite3)**: see §7.

### 6.1 Data Flows

**Registration**: client → `POST /api/auth/register` → normalize name → uniqueness check (`name_key`) → insert user → issue JWT → return `{userId, firstName, lastName, token}`.

**Login**: client → `POST /api/auth/login` → normalize name → lookup by `name_key` → if found, issue JWT and return `{userId, firstName, lastName, token}`; if not found, `404`.

**Activity ingestion**: client → `POST /api/activities` with `Authorization: Bearer <token>` → token middleware resolves `userId` → validate sport/metric pairing and value bounds → server generates `recorded_at` (UTC, now) and derives `activity_date` (IST calendar date of that instant) → if `daily_steps` and a row already exists for `(userId, activity_date)`, update its `step_count` and recompute points; otherwise insert → `computePoints()` → response echoes activity + points + server-generated `recordedAt`.

**Leaderboard read**: `GET /api/leaderboard` (no auth) → live aggregate `SUM(points) GROUP BY user_id` → apply tie-break ordering → for each user, look up the most recent snapshot's rank → compute `rankTrend` → return.

**Dashboard read**: `GET /api/users/{id}/dashboard` with `Authorization: Bearer <token>` → verify token's `userId == {id}`, else `403` → aggregate activity history, `volumeOverTime` (bucketed by `activity_date` / IST calendar day, converted from UTC by the backend), and `sportBreakdown` → return.

**Daily snapshot**: scheduler (00:00 IST) or CLI → `generate_daily_snapshot()` → target date = the IST calendar day that just completed → aggregate the leaderboard as of that day's end → apply tie-break rule → assign ranks → insert one `leaderboard_snapshots` row (`snapshot_date` = the completed day) + one `leaderboard_entries` row per user (idempotent per date via `UNIQUE(snapshot_date)`).

---

## 7. Database Schema

```sql
CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name    TEXT NOT NULL,
  last_name     TEXT NOT NULL,
  name_key      TEXT NOT NULL,          -- lower(trim(first)) || '|' || lower(trim(last)), whitespace-collapsed
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_users_name_key ON users(name_key);

CREATE TABLE activities (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL REFERENCES users(id),
  sport_type     TEXT NOT NULL CHECK (sport_type IN
                   ('running','walking','cycling','swimming','gym','daily_steps')),
  metric_type    TEXT NOT NULL CHECK (metric_type IN ('distance','duration','count')),
  distance_km    REAL,                  -- set only when metric_type = 'distance'
  duration_sec   INTEGER,               -- set only when metric_type = 'duration'
  step_count     INTEGER,               -- set only when metric_type = 'count'
  points         INTEGER NOT NULL,
  recorded_at    TEXT NOT NULL,         -- ISO 8601 instant the activity was recorded
  activity_date  TEXT NOT NULL,         -- IST calendar date ('YYYY-MM-DD'), computed in Python
                                         -- (zoneinfo "Asia/Kolkata") at write time — NEVER via a
                                         -- SQL date expression. This is the sole basis for all
                                         -- day-bucketing: daily-steps upsert, volumeOverTime,
                                         -- and the snapshot filter in §9.3.
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (
    (metric_type = 'distance' AND distance_km IS NOT NULL AND duration_sec IS NULL AND step_count IS NULL) OR
    (metric_type = 'duration' AND duration_sec IS NOT NULL AND distance_km IS NULL AND step_count IS NULL) OR
    (metric_type = 'count'    AND step_count  IS NOT NULL AND distance_km IS NULL AND duration_sec IS NULL)
  )
);
CREATE INDEX idx_activities_user_recorded ON activities(user_id, recorded_at);

-- Only ONE daily_steps row per user per IST calendar day
CREATE UNIQUE INDEX idx_daily_steps_unique
  ON activities(user_id, activity_date)
  WHERE sport_type = 'daily_steps';

CREATE TABLE leaderboard_snapshots (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_date  TEXT NOT NULL,         -- IST calendar date, 'YYYY-MM-DD' — the COMPLETED day this snapshot represents
  created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX idx_snapshot_date ON leaderboard_snapshots(snapshot_date);

CREATE TABLE leaderboard_entries (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_id    INTEGER NOT NULL REFERENCES leaderboard_snapshots(id),
  user_id        INTEGER NOT NULL REFERENCES users(id),
  rank           INTEGER NOT NULL,
  total_points   INTEGER NOT NULL
);
CREATE UNIQUE INDEX idx_entries_snapshot_user ON leaderboard_entries(snapshot_id, user_id);
CREATE INDEX idx_entries_user ON leaderboard_entries(user_id);
```

**Notes**:
- **Fixed storage convention**: `recorded_at` and `created_at` are always stored in UTC. `activity_date` is computed once, in the backend (Python `zoneinfo`, not SQL), at the moment a row is written — converting the server-generated UTC `recorded_at` into its IST calendar date. All later reads (daily-steps uniqueness, `volumeOverTime`, snapshot targeting) use this stored `activity_date` directly rather than re-deriving it from `recorded_at` at query time — one computation, one source of truth, no per-query timezone math.
- `CHECK` constraints enforce **structural** validity (correct field populated for the sport's metric type); the API layer separately enforces **business** validity (e.g. `distanceKm > 0`, not just non-null) — see R7 in §13.
- No table stores the session token — a JWT is stateless (`{userId, exp}`, signed), so no `sessions` table is needed for "basic" scope.

---

## 8. API Specification

### `POST /api/auth/register` (public)
```json
Request:  { "firstName": "Ada", "lastName": "Lovelace" }
201:      { "userId": 1, "firstName": "Ada", "lastName": "Lovelace", "token": "<jwt>" }
409:      { "error": "USER_ALREADY_EXISTS", "message": "A user with this name is already registered." }
400:      { "error": "VALIDATION_ERROR", "message": "firstName and lastName are required strings." }
```

### `POST /api/auth/login` (public)
```json
Request:  { "firstName": "Ada", "lastName": "Lovelace" }
200:      { "userId": 1, "firstName": "Ada", "lastName": "Lovelace", "token": "<jwt>" }
404:      { "error": "USER_NOT_FOUND", "message": "No user matches this name." }
400:      { "error": "VALIDATION_ERROR", "message": "firstName and lastName are required strings." }
```

### `POST /api/activities` (requires `Authorization: Bearer <token>`)
`userId` is derived from the token — **not** accepted as a body field.
```json
// distance sports
{ "sportType": "running", "distanceKm": 5.3 }
// duration sports
{ "sportType": "swimming", "durationSec": 1855 }
// steps
{ "sportType": "daily_steps", "stepCount": 8342 }

201: { "activityId": 10, "sportType": "running", "points": 530, "recordedAt": "2026-08-13T01:30:00Z" }
200: { "activityId": 10, "sportType": "daily_steps", "points": 83, "recordedAt": "2026-08-13T12:45:00Z", "updated": true }  // steps upsert case
400: { "error": "VALIDATION_ERROR", "message": "sportType 'running' requires distanceKm (number > 0)." }
401: { "error": "UNAUTHORIZED", "message": "Missing or invalid session token." }
```
`recordedAt` is **always server-generated** (current UTC instant) — it is never accepted from the client, and any `recordedAt` field present in the request body is ignored (not merely optional). Sport→field validation map: `running/walking/cycling` → `distanceKm: number > 0`; `swimming/gym` → `durationSec: integer ≥ 0`; `daily_steps` → `stepCount: integer ≥ 0`. Any extra/mismatched field (including a client-supplied `recordedAt`, `userId`, or `activity_date`) → `400`.

### `GET /api/leaderboard` (public)
```json
[
  { "rank": 1, "userId": 2, "name": "Snegith V", "totalPoints": 4800, "rankTrend": 2 },
  { "rank": 2, "userId": 1, "name": "Ada Lovelace", "totalPoints": 4500, "rankTrend": -1 },
  { "rank": 3, "userId": 3, "name": "Grace Hopper", "totalPoints": 4500, "rankTrend": null }
]
```
`rankTrend = previousRank − currentRank` (positive = improved); `null` if the user has no prior snapshot. Ties broken by `created_at ASC, userId ASC`.

**Zero-activity users**: The leaderboard includes ALL registered users, including those who have not yet logged any activity. These users appear with `totalPoints: 0` via a `LEFT JOIN` / `COALESCE(SUM(points), 0)` query. This ensures newly registered users see themselves on the leaderboard immediately.

### `GET /api/users/{id}/dashboard` (requires `Authorization: Bearer <token>`; token's `userId` must equal `{id}`)
```json
200: {
  "totalPoints": 4210,
  "activityHistory": [ { "activityId": 10, "sportType": "running", "points": 530, "recordedAt": "..." } ],
  "volumeOverTime": [ { "date": "2026-08-13", "points": 210 } ],   // grouped by stored activity_date
  "sportBreakdown": { "running": 2100, "gym": 1200 }
}
403: { "error": "FORBIDDEN", "message": "Cannot access another user's dashboard." }
404: { "error": "USER_NOT_FOUND" }
401: { "error": "UNAUTHORIZED", "message": "Missing or invalid session token." }
```
Empty-activity case returns `200` with `totalPoints: 0`, empty arrays, empty `sportBreakdown` — never a `404`.

**Response field semantics**:
- `activityHistory` is ordered by `recorded_at` **descending** (most recent activity first).
- `volumeOverTime` is ordered by `activity_date` (the stored IST calendar date) **ascending**. It is **sparse** — only dates with at least one logged activity are included; dates with no activity are not zero-filled.
- `sportBreakdown` maps each `sport_type` the user has logged to the sum of points for that sport. Sports with zero points are omitted.

### Endpoint Summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Create user, issue token |
| POST | `/api/auth/login` | Public | Re-issue token for existing user |
| POST | `/api/activities` | Bearer token | Log/upsert an activity |
| GET | `/api/leaderboard` | Public | Live ranked leaderboard + trend |
| GET | `/api/users/{id}/dashboard` | Bearer token (self only) | Personal stats |

*(No HTTP endpoint triggers snapshot generation — see §6, "Scheduler," and R9 in §13.)*

---

## 9. Scoring, Normalization & Ranking Logic

### 9.1 Points Conversion

| Sport | Metric | Rate | Flooring rule |
|---|---|---|---|
| Running | km | 100 pts/km | `floor(km * 100)` |
| Walking | km | 50 pts/km | `floor(km * 50)` |
| Cycling | km | 25 pts/km | `floor(km * 25)` |
| Swimming | min | 15 pts/min | `floor(sec / 60) * 15` |
| Gym | min | 5 pts/min | `floor(sec / 60) * 5` |
| Daily Steps | 100 steps | 1 pt | `floor(stepCount / 100)` |

Implemented as a single pure `compute_points(sport_type, metric_value)` function, table-driven, no DB/HTTP dependency. Unit tested directly against the spec's own worked examples (1.55 km walking → 77, 1:55 → floors to 1 min, 399 steps → 3 pts) plus zero-value and boundary cases (exactly 60s, exactly 100/200/399 steps).

Points are computed at write time and stored — not recomputed on read — except for the `daily_steps` upsert case, where the existing row's points are explicitly recalculated in place when the step count is updated (FR-10).

### 9.2 Leaderboard Ranking
- Primary sort: `totalPoints` descending.
- Tie-break 1: `created_at` (registration time) ascending — earlier-registered user ranks higher.
- Tie-break 2: `userId` ascending.

### 9.3 Rank Trend
Computed only at read time for the live GET /api/leaderboard response: rankTrend = mostRecentSnapshotRank − currentLiveRank. null when no snapshot exists yet for that user.

Snapshot generation rule: generate_daily_snapshot(target_date) computes the leaderboard using only activities whose activity_date <= target_date. This applies whether the function is invoked by the scheduler (where target_date is always "yesterday" relative to the 00:00 IST trigger) or manually via the CLI for a backdated date. A run for target_date = Aug 13 triggered on Aug 16 must exclude any activity dated Aug 14–16 — the snapshot always reflects the state as of the end of target_date, regardless of when generation actually happens. This is what makes the scheduler path and the CLI path produce identical results for the same target_date, satisfying NFR-7.

---

## 10. Frontend Architecture & UI Flow

```
src/
  api/client.js              -- fetch wrapper, attaches Authorization header from stored token
  pages/
    Register.jsx
    Login.jsx
    LogActivity.jsx
    Leaderboard.jsx
    Dashboard.jsx
  components/
    LeaderboardTable.jsx      -- rank, name, points, rankTrend arrow ("New" if null)
    VolumeOverTimeChart.jsx   -- line chart (recharts), points/IST-day
    SportBreakdownChart.jsx   -- pie/bar chart, points by sport
    ActivityHistoryList.jsx
```

```
Landing
  │
  ├─ stored token exists? ──▶ Dashboard
  └─ no token ──▶ Register / Login ──▶ store token ──▶ Dashboard

Dashboard / Leaderboard (nav accessible from either)
  │
  └─ Log Activity ──▶ sport picker ──▶ conditional field
                       (distance / duration / count)
                     ──▶ submit ──▶ inline confirmation with points

"Switch user" action available from Dashboard — clears the stored token
and returns to Register/Login (no server-side session to invalidate,
since the token is a stateless JWT).
```

---

## 11. Test Plan

### 11.1 Unit — scoring service
- Each sport's conversion rate against a known input/output pair.
- Flooring boundaries: exact km values; exact minute boundaries (60s, 119s, 120s); exact 100-step boundaries (100, 199, 200, 399).
- Zero-value inputs → 0 points, not an error.

### 11.2 Unit — ranking/tie-break
- Two users with identical `totalPoints`: verify ordering by `created_at`, then `userId`.
- `rankTrend` calculation against a known prior-snapshot fixture, including the `null` (no-prior-snapshot) case.

### 11.3 Integration — auth
- Register → receive token → token successfully authorizes a protected request.
- Login with matching name → new token issued for the correct existing `userId`.
- Login with non-matching name → `404`.
- Protected endpoint with missing/expired/malformed token → `401`.
- Dashboard request where token's `userId` ≠ path `{id}` → `403`.

### 11.4 Integration — activities
- Valid payload per sport (6 cases) → correct points; `recordedAt` in the response is server-generated UTC, not echoed from the request.
- A `recordedAt` field included in the request body is ignored/rejected, never used to set the stored timestamp.
- Mismatched sport/metric field → `400`.
- Second `daily_steps` submission with the same computed `activity_date` → existing row updated, points recalculated, no duplicate row (verify via `SELECT COUNT(*)` and via the `idx_daily_steps_unique` constraint).
- `daily_steps` submission that computes to a new `activity_date` → new row inserted.

### 11.5 Integration — leaderboard & snapshot
- Ordering correctness with multiple users, including a tie.
- Snapshot generation (via CLI trigger, run "at" a simulated 00:00 IST) targets and stores the **completed previous day**, not the day the job runs on.
- Snapshot generation produces one `leaderboard_snapshots` row + N `leaderboard_entries` rows.
- Re-running snapshot generation for a target date that already has a snapshot does not create a duplicate (`UNIQUE(snapshot_date)` enforced, verify rejection/no-op behavior).
- `rankTrend` on live leaderboard correctly reflects a seeded prior-day snapshot, using `previousRank − currentRank`.
- A manually-triggered snapshot for a backdated target_date must include only activities with activity_date <= target_date, and must exclude any activity recorded after target_date even though it already exists in the table at generation time.

### 11.6 Concurrency
- Two simultaneous registration requests with identical names → exactly one succeeds, one returns `409`.

### 11.7 Frontend
- Form validation blocks empty/invalid fields before submit.
- Conditional field rendering per selected sport.
- Token attached automatically on protected requests; absent on public ones.
- Leaderboard/dashboard render correctly from mocked API responses, including empty-state.

### 11.8 Manual / exploratory
- End-to-end: register → log one activity per sport → verify points → verify leaderboard position and (after a manual snapshot trigger + new activity) a non-null `rankTrend` → verify dashboard breakdown sums to total → "switch user" and repeat as a second user to see relative leaderboard movement.

---

## 12. Known Limitations

- Duplicate-user detection is name-only — two real people sharing a name is a documented false-positive risk, not resolved by session tokens.
- Session tokens provide identification, not authentication — no credential is verified at registration or login (§2.3, NFR-6).
- Leaderboard has no pagination — assumed acceptable at assignment scale.
- Rank trend is only as fresh as the last snapshot; multiple rank changes within a single day are not individually tracked, only the net day-over-day change.

---

## 13. Risk & Assumptions Log

| # | Assumption / Decision | Rationale | Impact if wrong | Status |
|---|---|---|---|---|
| R1 | Session-token identification only, no password | Client confirmed auth is optional/bonus; "basic" scope agreed | If real credential auth is expected later, requires a rebuild of the identity layer | Resolved |
| R2 | Duplicate-user detection is name-only | Directly specified by the assignment | Name collisions between real distinct people are indistinguishable | Accepted (spec-mandated) |
| R3 | Leaderboard is live-computed, snapshot used only for trend baseline | Instant feedback after logging an activity preserves the gamification hook | — | Resolved |
| R4 | Points computed once at write time; recomputed only on the `daily_steps` upsert path | Keeps reads cheap; steps is the one sport with mutable-in-place semantics by design | A future sport added with similar "daily rollup" semantics would need the same explicit recompute-on-update handling | Resolved |
| R5 | Rank trend requires historical snapshots | Required a schema addition (`leaderboard_snapshots`, `leaderboard_entries`) | — | Resolved |
| R6 | Daily steps use replace (not increment) semantics; points recalculated on the existing row | Client confirmed device sends cumulative daily total | If this assumption is wrong, totals would silently overwrite valid data instead of accumulating | Resolved |
| R7 | DB `CHECK` allows `≥ 0` on metric fields; API layer separately rejects `≤ 0` | Intentional layering — DB enforces structural validity, API enforces business validity | Low — documented so it doesn't read as inconsistent in review | Accepted (documented) |
| R8 | Local-run deployment with setup instructions, not a hosted public URL | Assignment requires a public **repo**, not explicit hosting | NEOGOV confirmed no hosting or deployment target is required; a local-run submission with setup instructions is sufficient | Resolved |
| R9 | No HTTP endpoint for snapshot generation; CLI + scheduler share one function instead | Avoids an unauthenticated (or under-specified-auth) write surface once tokens are in the picture | None identified — CLI trigger fully covers testing/demo needs | Resolved |
| R10 | JWT expiry set to 24h, no refresh-token flow | "Basic" auth scope explicitly agreed; refresh flows are out of scope for optional/bonus work | User re-logs-in (name lookup) after expiry — low friction given no password | Accepted (documented) |
| R11 | `recordedAt` is server-generated only; client cannot supply or backdate it | Removes timezone-interpretation ambiguity and a leaderboard-gaming vector (backdating activities) | None identified | Resolved |
| R12 | Timestamps stored in UTC; all date-bucketing computed by the backend (`zoneinfo`) into an explicit `activity_date` column, not via SQL offset expressions | Portable, debuggable, avoids the fragility of expression-based indexes; single source of truth reused by steps-uniqueness, `volumeOverTime`, and snapshot targeting | None identified | Resolved |
| R13 | Midnight (00:00 IST) snapshot represents the just-completed previous day, not the day starting | Required for `rankTrend` to compare against a fully-settled day rather than a day still in progress | Getting this backwards would make every trend value off-by-one-day and effectively meaningless | Resolved |

---

## 14. Frontend Requirements

The following documents the implemented frontend behaviour as user-facing requirements.

### 14.1 Navigation & Authentication Flow

- FR-FE-1: When no token is stored, the user sees Register and Login pages. Authenticated routes (Dashboard, Log Activity) redirect to Login.
- FR-FE-2: When a valid token is stored, the user is redirected from Register/Login to Dashboard. The navigation displays: Dashboard, Log Activity, Leaderboard, Help, and Log Out.
- FR-FE-3: Leaderboard and Help are accessible without authentication (public pages).
- FR-FE-4: Log Out clears the stored token and redirects to Login. No server-side session invalidation occurs (JWT is stateless).
- FR-FE-5: The default route (`/`) redirects authenticated users to Dashboard and unauthenticated users to Leaderboard.

### 14.2 Activity Logging

- FR-FE-6: The Log Activity page presents six sport types as a radio-button group: Running, Walking, Cycling, Swimming, Gym, Daily Steps.
- FR-FE-7: Selecting a sport conditionally renders the appropriate input field(s): distance (km) for Running/Walking/Cycling; Hours + Minutes for Swimming/Gym; step count for Daily Steps.
- FR-FE-8: Duration-based sports (Swimming, Gym) accept separate Hours and Minutes inputs. The frontend converts these to `durationSec = hours × 3600 + minutes × 60` before submission.
- FR-FE-9: Client-side validation blocks submission of invalid values (empty, negative, zero distance) with an inline error message.
- FR-FE-10: On successful submission, the earned points are displayed prominently. The user can log another activity or navigate to the dashboard.
- FR-FE-11: The frontend never computes authoritative points. Points are always taken from the server response.

### 14.3 Dashboard

- FR-FE-12: The Dashboard displays the user's total points in a prominent score display with odometer-style animation on change.
- FR-FE-13: The Sport Breakdown section shows a horizontal bar chart of points per sport, sorted by points descending. Empty state: "No activities yet."
- FR-FE-14: The Volume Over Time section shows an area chart (Recharts) of points per day when 3+ data points exist. For 1–2 data points, a compact numeric summary is shown. Empty state: "No data yet."
- FR-FE-15: The Recent Activity section shows up to 20 most recent activities (sport type + points earned). Empty state: "No activities logged yet."

### 14.4 Leaderboard

- FR-FE-16: The Leaderboard page displays all participants in a table with columns: Rank, Player (title-cased name), Points (comma-formatted), Trend.
- FR-FE-17: Rank trend display: positive → green up-arrow with magnitude; negative → red down-arrow with magnitude; zero → dash; null → "NEW" badge.
- FR-FE-18: The current authenticated user's row (if any) is visually highlighted.
- FR-FE-19: Empty leaderboard state: "No participants yet."

### 14.5 Help Page

- FR-FE-20: The Help page explains the scoring system (all six sports with rates and examples), activity logging instructions, daily steps replacement semantics, dashboard contents, leaderboard ranking and trend logic, and account/identity model.

### 14.6 Timestamp & Number Display

- FR-FE-21: Points are formatted with locale-appropriate thousand separators (e.g., "5,090").
- FR-FE-22: Player names are displayed in title case on the leaderboard.

