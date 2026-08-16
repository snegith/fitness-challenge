import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Help from "../src/pages/Help";

describe("Help", () => {
  it("renders scoring table", () => {
    render(<Help />);
    expect(screen.getByText("100 pts / km")).toBeInTheDocument();
    expect(screen.getByText("50 pts / km")).toBeInTheDocument();
    expect(screen.getByText("15 pts / min")).toBeInTheDocument();
    expect(screen.getByText("5 pts / min")).toBeInTheDocument();
    expect(screen.getByText("1 pt / 100 steps")).toBeInTheDocument();
  });

  it("explains daily steps replacement", () => {
    render(<Help />);
    expect(screen.getByText(/replaces/i)).toBeInTheDocument();
  });

  it("explains ranking tie-break", () => {
    render(<Help />);
    expect(screen.getByText(/registration date/i)).toBeInTheDocument();
  });
});
