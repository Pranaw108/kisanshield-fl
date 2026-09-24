import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PredictResponse } from "../types";
import { ResultCard } from "./ResultCard";

const CONFIDENT: PredictResponse = {
  status: "ok",
  top: { class_id: "SOY_RUST", name_en: "Rust", name_hi: "गेरुआ रोग", crop: "soybean", confidence: 0.91 },
  alternatives: [
    { class_id: "SOY_FROGEYE", name_en: "Frogeye leaf spot", name_hi: "फ्रॉगआई पत्ती धब्बा", crop: "soybean", confidence: 0.05 },
  ],
  message: null,
};

const UNSURE: PredictResponse = {
  status: "not_sure",
  top: null,
  alternatives: [],
  message: "Not confident enough to name a disease.",
};

describe("ResultCard", () => {
  it("shows the top prediction and its Hindi name", () => {
    render(<ResultCard result={CONFIDENT} />);
    expect(screen.getByText("Rust")).toBeInTheDocument();
    expect(screen.getByText("गेरुआ रोग")).toBeInTheDocument();
    expect(screen.getByText("91% confidence")).toBeInTheDocument();
  });

  it("lists alternatives", () => {
    render(<ResultCard result={CONFIDENT} />);
    expect(screen.getByText("Frogeye leaf spot")).toBeInTheDocument();
    expect(screen.getByText("5%")).toBeInTheDocument();
  });

  it("never shows treatment advice — none exists until an expert approves it", () => {
    render(<ResultCard result={CONFIDENT} />);
    expect(screen.queryByText(/spray|treatment|apply|dose/i)).not.toBeInTheDocument();
  });

  it("shows a not-sure message instead of a disease when confidence is low", () => {
    render(<ResultCard result={UNSURE} />);
    expect(screen.getByText("Not sure")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});
