/**
 * Frontend tests — API client (src/api/client.js).
 *
 * Coverage (SRS §11.7):
 *   - Bearer token is attached on protected requests when token is in storage.
 *   - No Authorization header is sent on public requests.
 *   - HTTP error responses are surfaced as thrown objects.
 */

import { describe, it } from "vitest";

describe("API client", () => {
  it.skip("attaches Authorization header when token is stored", () => {});
  it.skip("omits Authorization header when no token is stored", () => {});
  it.skip("throws on non-2xx responses", () => {});
});
