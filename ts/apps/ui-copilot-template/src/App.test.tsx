import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the app header branding", () => {
    render(<App />);
    expect(screen.getByText("Azure AI Copilot")).toBeInTheDocument();
  });

  it("renders the disclaimer text", () => {
    render(<App />);
    const disclaimers = screen.getAllByText(/AI-generated responses/i);
    expect(disclaimers.length).toBeGreaterThanOrEqual(1);
  });
});
