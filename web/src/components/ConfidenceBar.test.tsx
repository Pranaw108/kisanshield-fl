import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConfidenceBar } from "./ConfidenceBar";

describe("ConfidenceBar", () => {
  it("shows the rounded percentage", () => {
    render(<ConfidenceBar confidence={0.916} />);
    expect(screen.getByText("92% confidence")).toBeInTheDocument();
  });

  it("sets the progressbar's value for assistive tech", () => {
    render(<ConfidenceBar confidence={0.5} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  });
});
