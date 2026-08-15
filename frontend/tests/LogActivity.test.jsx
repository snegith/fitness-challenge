/**
 * Frontend tests — LogActivity page.
 *
 * Coverage (SRS §11.7):
 *   - Selecting a distance sport renders distanceKm field only.
 *   - Selecting a duration sport renders durationSec field only.
 *   - Selecting daily_steps renders stepCount field only.
 *   - Empty/missing required field → form validation blocks submission.
 *   - On success: inline confirmation with awarded points is displayed.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// import LogActivity from "../src/pages/LogActivity";

describe("LogActivity", () => {
  it.skip("renders distanceKm field for distance sports", () => {});
  it.skip("renders durationSec field for duration sports", () => {});
  it.skip("renders stepCount field for daily_steps", () => {});
  it.skip("blocks submission when required field is empty", () => {});
  it.skip("displays points confirmation on success", () => {});
});
