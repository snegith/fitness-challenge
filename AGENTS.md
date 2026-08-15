# Project Engineering Rules

## 1. Source of Truth

- `SRS.md` is the authoritative source of requirements and design decisions.
- Do not invent, remove, or modify requirements without explicit approval.
- If an implementation detail is ambiguous or conflicts with the SRS, stop and ask for clarification rather than silently making a product decision.
- Keep implementation aligned with the finalized SRS.
- Any intentional deviation from the SRS must be explicitly documented before implementation.
- R8 in the SRS Risk Log (hosting/deployment target) is explicitly **unresolved**. Do not assume local-only, a specific host, or any deployment target — stop and ask before making a hosting decision of any kind.

## 2. Architecture

- Frontend: React.
- Backend: Python + FastAPI.
- Database: SQLite.
- Backend is the authoritative source for validation, scoring, and business rules.
- Frontend must never be the authoritative source for point calculation.
- Keep API routes, business logic, database access, and schemas separated.
- Prefer simple, maintainable architecture appropriate for the scale of this assignment.
- Do not introduce unnecessary infrastructure, microservices, caching, or external dependencies.

## 3. Business Logic

- Scoring logic must remain a pure, independently testable function.
- All point calculations happen server-side.
- Computed points are persisted with the activity.
- Daily Steps use replace/upsert semantics for the user's current daily total.
- Daily Steps updates must be atomic.
- Concurrent same-day Daily Steps submissions must be handled via the database's unique constraint, not a check-then-act pattern alone: if a concurrent insert violates the per-user/per-day uniqueness constraint, catch it and fall back to an update rather than surfacing a raw database error.
- Leaderboard ranking is live and derived from current activity data.
- Daily leaderboard snapshots are historical baselines used for ranking trends.
- The daily snapshot represents the immediately preceding completed calendar day. `snapshot_date` must be stored as the date being summarized, not the date the job executed (a job running at 00:00 IST on day N stores `snapshot_date = N-1`).
- All date-based business logic uses the configured `Asia/Kolkata` timezone.
- Timestamps must follow the finalized timezone/storage convention in the SRS. If the UTC-vs-IST storage convention for `recorded_at` is not yet pinned down when this is first implemented, stop and ask rather than picking one silently.

## 4. API

- Follow the API contract defined in `SRS.md`.
- Do not add undocumented endpoints or change request/response structures without approval.
- Use consistent HTTP status codes and error response formats.
- Validate all client input at the API boundary.
- Never trust client-provided points.
- Never trust a client-provided `userId` on protected endpoints — derive identity from the verified session token only.
- Authentication/session information must be handled server-side.
- Keep API behavior deterministic and predictable.

## 5. Database

- Follow the finalized database schema in `SRS.md`.
- Enforce important integrity rules at the database level where appropriate.
- Preserve foreign-key relationships and uniqueness constraints.
- Daily Steps must have the required per-user/per-day uniqueness constraint.
- Use transactions for operations that must be atomic.
- Do not store derived data unnecessarily unless explicitly required by the architecture, such as leaderboard snapshots.

## 6. Testing

- Every significant business rule must have automated tests.
- Scoring must have unit tests covering normal values and flooring/boundary cases.
- Test Daily Steps insert, update, duplicate/concurrent submissions, and point recalculation.
- Test leaderboard ranking, tie-breaking, and rank trends.
- Test timezone/date-boundary behavior.
- Test daily snapshot generation.
- Test API validation and error responses.
- Test concurrent registration requests for uniqueness enforcement (exactly one request must succeed, others must return 409).
- Test authorization behavior: missing/invalid/expired token on a protected endpoint returns 401; a valid token whose `userId` does not match the requested dashboard `{id}` returns 403.
- Add regression tests whenever a bug is discovered.
- Do not remove or weaken tests simply to make the test suite pass.

## 7. Code Quality

- Prefer readable, explicit code over clever or unnecessarily abstract code.
- Follow consistent naming conventions.
- Keep functions and modules focused on one responsibility.
- Avoid duplicated business logic.
- Do not leave debugging statements, dead code, unused imports, or temporary files in committed code.
- Handle errors explicitly.
- Do not suppress exceptions without a documented reason.
- Add comments only where they explain non-obvious decisions or business rules.



## 8. Git & Branching Workflow

### Repository Structure

- The `main` branch must always represent stable, reviewable code.
- Do not develop directly on `main`.
- All implementation work must happen on feature, fix, refactor, test, or documentation branches.
- Keep branches short-lived and focused on one logical change.

### Branch Naming

Use descriptive branch names such as:

- `feature/scoring-engine`
- `feature/activity-api`
- `feature/leaderboard`
- `feature/dashboard`
- `feature/authentication`
- `feature/frontend-activity-form`
- `test/scoring-boundaries`
- `fix/daily-steps-upsert`
- `refactor/leaderboard-service`
- `docs/update-srs`

### Commits

- Commits must be small, focused, and logically coherent.
- Do not create large "implement everything" commits.
- Each commit should represent one meaningful change.
- Use clear conventional commit-style messages.

Examples:

- `docs: finalize SRS`
- `chore: scaffold FastAPI backend`
- `feat: add scoring engine`
- `test: add scoring boundary cases`
- `feat: implement activity API`
- `fix: handle daily steps upsert`
- `feat: add live leaderboard`
- `feat: add daily leaderboard snapshots`
- `test: add leaderboard ranking tests`
- `refactor: separate leaderboard service`
- `docs: update API contract`

- Do not mix unrelated changes in the same commit.
- Do not commit generated files, secrets, local databases, environment files, IDE metadata, or temporary artifacts unless explicitly required.
- Never commit `.env` files containing secrets, including the JWT signing key.

### Pull Requests

- Every completed feature or logical unit of work must be merged through a Pull Request.
- Do not merge feature branches directly into `main`.
- PRs should have:
  - A clear title.
  - A concise description of what changed.
  - The requirement/SRS section being implemented.
  - Testing performed.
  - Any design decisions or deviations.
  - Any known limitations.
- Keep PRs reasonably small and reviewable.
- Before opening a PR:
  - Run the relevant test suite.
  - Verify the application starts correctly.
  - Check formatting/linting where configured.
  - Review the diff for accidental changes.
  - Ensure no secrets or temporary files are included.
- PR titles should follow the same conventional style as commits.

Example:

`feat: implement activity ingestion API`

PR description:

```md
## Summary
Implements activity ingestion and server-side point calculation.

## SRS Requirements
- FR-6 Activity submission
- FR-7 Activity validation
- FR-8 Point calculation
- FR-9 Point persistence

## Testing
- Scoring unit tests
- Activity API integration tests
- Validation/error cases

## Notes
No deviations from the SRS.
```