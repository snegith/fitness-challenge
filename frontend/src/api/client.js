/**
 * API client — fetch wrapper used by all pages and components.
 *
 * Responsibilities (SRS §10):
 *   - Attach `Authorization: Bearer <token>` on every request when a token
 *     is present in storage.
 *   - Public endpoints (register, login, leaderboard) receive no token header.
 *   - Return parsed JSON responses; surface HTTP errors as thrown objects.
 *
 * The token is stored client-side (localStorage).  It is a stateless JWT —
 * no server-side session exists (SRS §2.3).
 */

// TODO: implement request(), get(), post() helpers
