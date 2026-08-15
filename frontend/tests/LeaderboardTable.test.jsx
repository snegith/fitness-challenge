/**
 * Frontend tests — LeaderboardTable component.
 *
 * Coverage (SRS §11.7):
 *   - Renders rank, name, points for each entry.
 *   - Positive rankTrend → up-arrow indicator.
 *   - Negative rankTrend → down-arrow indicator.
 *   - null rankTrend → "New" label.
 *   - Empty entries array → empty state message.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// import LeaderboardTable from "../src/components/LeaderboardTable";

describe("LeaderboardTable", () => {
  it.skip("renders entries correctly", () => {});
  it.skip("shows up arrow for positive rankTrend", () => {});
  it.skip("shows down arrow for negative rankTrend", () => {});
  it.skip("shows New label for null rankTrend", () => {});
  it.skip("shows empty state for empty entries", () => {});
});
