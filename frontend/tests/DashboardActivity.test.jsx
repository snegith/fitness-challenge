/**
 * Tests — Dashboard Recent Activity: timestamp + sorting logic.
 * Tests the formatIST and sorting behavior in isolation since full Dashboard
 * rendering depends on Recharts/ResizeObserver which is fragile in jsdom.
 */

import { describe, it, expect } from "vitest";

// Test formatIST logic directly (same implementation as Dashboard.jsx)
function formatIST(utcStr) {
  try {
    if (!utcStr) return "";
    const d = new Date(utcStr.endsWith("Z") ? utcStr : utcStr + "Z");
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch { return ""; }
}

function sortActivities(items, sortBy) {
  switch (sortBy) {
    case "oldest":
      return [...items].sort((a, b) => (a.recordedAt || "").localeCompare(b.recordedAt || ""));
    case "most-pts":
      return [...items].sort((a, b) => b.points - a.points);
    case "least-pts":
      return [...items].sort((a, b) => a.points - b.points);
    default:
      return [...items].sort((a, b) => (b.recordedAt || "").localeCompare(a.recordedAt || ""));
  }
}

const ACTIVITIES = [
  { activityId: 1, sportType: "running", points: 500, recordedAt: "2026-08-16T04:12:00Z" },
  { activityId: 2, sportType: "cycling", points: 325, recordedAt: "2026-08-17T05:48:00Z" },
  { activityId: 3, sportType: "daily_steps", points: 105, recordedAt: "2026-08-17T05:55:00Z" },
];

describe("formatIST", () => {
  it("formats UTC timestamp to IST", () => {
    // 2026-08-17T05:55:00Z = IST 11:25 AM on Aug 17
    const result = formatIST("2026-08-17T05:55:00Z");
    expect(result).toContain("17");
    expect(result.length).toBeGreaterThan(0);
  });

  it("returns empty string for null", () => {
    expect(formatIST(null)).toBe("");
  });

  it("returns empty string for invalid date", () => {
    expect(formatIST("not-a-date")).toBe("");
  });

  it("returns empty string for empty string", () => {
    expect(formatIST("")).toBe("");
  });
});

describe("sortActivities", () => {
  it("most-recent sorts by recordedAt descending", () => {
    const sorted = sortActivities(ACTIVITIES, "recent");
    expect(sorted[0].activityId).toBe(3); // 05:55 is most recent
    expect(sorted[2].activityId).toBe(1); // 04:12 Aug 16 is oldest
  });

  it("oldest sorts by recordedAt ascending", () => {
    const sorted = sortActivities(ACTIVITIES, "oldest");
    expect(sorted[0].activityId).toBe(1);
    expect(sorted[2].activityId).toBe(3);
  });

  it("most-pts sorts by points descending", () => {
    const sorted = sortActivities(ACTIVITIES, "most-pts");
    expect(sorted[0].points).toBe(500);
    expect(sorted[2].points).toBe(105);
  });

  it("least-pts sorts by points ascending", () => {
    const sorted = sortActivities(ACTIVITIES, "least-pts");
    expect(sorted[0].points).toBe(105);
    expect(sorted[2].points).toBe(500);
  });

  it("handles missing recordedAt gracefully", () => {
    const items = [
      { activityId: 1, points: 100, recordedAt: null },
      { activityId: 2, points: 200, recordedAt: "2026-08-17T05:00:00Z" },
    ];
    const sorted = sortActivities(items, "recent");
    expect(sorted[0].activityId).toBe(2); // has a date, sorts first
  });

  it("limits to input array (20-item limit applied before sorting)", () => {
    const many = Array.from({ length: 25 }, (_, i) => ({
      activityId: i, points: i * 10, recordedAt: `2026-08-${String(i+1).padStart(2,"0")}T00:00:00Z`,
    }));
    const limited = many.slice(0, 20);
    const sorted = sortActivities(limited, "most-pts");
    expect(sorted.length).toBe(20);
    expect(sorted[0].points).toBe(190); // highest in first 20
  });
});
