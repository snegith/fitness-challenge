import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

beforeEach(() => { localStorage.clear(); global.fetch = vi.fn(); });
afterEach(() => { vi.restoreAllMocks(); });

describe("API client", () => {
  it("attaches Authorization header when token is stored", async () => {
    localStorage.setItem("token", "test-jwt");
    global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });
    const { get } = await import("../src/api/client.js");
    await get("/api/leaderboard");
    expect(global.fetch.mock.calls[0][1].headers["Authorization"]).toBe("Bearer test-jwt");
  });

  it("omits Authorization when auth=false", async () => {
    localStorage.setItem("token", "test-jwt");
    global.fetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });
    const { get } = await import("../src/api/client.js");
    await get("/api/leaderboard", { auth: false });
    expect(global.fetch.mock.calls[0][1].headers["Authorization"]).toBeUndefined();
  });

  it("throws on non-2xx with status", async () => {
    global.fetch.mockResolvedValueOnce({ ok: false, status: 404, json: () => Promise.resolve({ error: "NOT_FOUND", message: "x" }) });
    const { get } = await import("../src/api/client.js");
    await expect(get("/api/x")).rejects.toMatchObject({ status: 404 });
  });
});
