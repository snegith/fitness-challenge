import { describe, it, expect } from "vitest";
import { titleCase, formatNumber } from "../src/utils/displayName";

describe("titleCase", () => {
  it("capitalizes lowercase", () => expect(titleCase("snegith")).toBe("Snegith"));
  it("normalizes ALLCAPS", () => expect(titleCase("VASU")).toBe("Vasu"));
  it("normalizes mixed", () => expect(titleCase("sNeGiTh")).toBe("Snegith"));
  it("multi-word", () => expect(titleCase("ada lovelace")).toBe("Ada Lovelace"));
  it("empty", () => expect(titleCase("")).toBe(""));
  it("null", () => expect(titleCase(null)).toBe(""));
});

describe("formatNumber", () => {
  it("formats thousands", () => expect(formatNumber(5090)).toBe("5,090"));
  it("zero", () => expect(formatNumber(0)).toBe("0"));
});
