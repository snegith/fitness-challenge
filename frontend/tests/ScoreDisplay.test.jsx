import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ScoreDisplay from "../src/components/ScoreDisplay";

describe("ScoreDisplay", () => {
  it("renders initial value without rolling", () => {
    render(<ScoreDisplay value={5090} />);
    expect(screen.getByTestId("score-display")).toHaveTextContent("5,090");
    expect(screen.getByTestId("score-display").querySelectorAll(".score-display__digit--roll").length).toBe(0);
  });

  it("triggers roll on value change", () => {
    vi.useFakeTimers();
    const { rerender } = render(<ScoreDisplay value={100} />);
    rerender(<ScoreDisplay value={200} />);
    expect(screen.getByTestId("score-display").querySelectorAll(".score-display__digit--roll").length).toBeGreaterThan(0);
    act(() => { vi.advanceTimersByTime(500); });
    expect(screen.getByTestId("score-display")).toHaveTextContent("200");
    vi.useRealTimers();
  });

  it("has accessible label", () => {
    render(<ScoreDisplay value={1234} />);
    expect(screen.getByLabelText("1234 points")).toBeInTheDocument();
  });
});
