import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../src/context/AuthContext";
import LogActivity from "../src/pages/LogActivity";

function renderPage() {
  localStorage.setItem("token", "t"); localStorage.setItem("userId", "1");
  return render(<MemoryRouter><AuthProvider><LogActivity /></AuthProvider></MemoryRouter>);
}

describe("LogActivity", () => {
  it("renders all six sport buttons", () => {
    renderPage();
    expect(screen.getByRole("radio", { name: /running/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /walking/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /cycling/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /swimming/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /gym/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /daily steps/i })).toBeInTheDocument();
  });

  it("shows distance input for running", () => {
    renderPage();
    fireEvent.click(screen.getByRole("radio", { name: /running/i }));
    expect(screen.getByPlaceholderText(/5\.3/)).toBeInTheDocument();
  });

  it("shows hours+minutes for swimming", () => {
    renderPage();
    fireEvent.click(screen.getByRole("radio", { name: /swimming/i }));
    expect(screen.getByText("Hours")).toBeInTheDocument();
    expect(screen.getByText("Minutes")).toBeInTheDocument();
  });

  it("shows step count for daily steps", () => {
    renderPage();
    fireEvent.click(screen.getByRole("radio", { name: /daily steps/i }));
    expect(screen.getByPlaceholderText(/8342/)).toBeInTheDocument();
  });
});
