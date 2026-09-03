import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HypothesisPanel } from "@/components/hypothesis-panel";
import type { HypothesisPayload } from "@/lib/api-client";

const HYPOTHESIS: HypothesisPayload = {
  id: "hyp-1",
  statement: "The change is primarily driven by order_volume.",
  status: "supported",
  confidence: "high",
  supporting_evidence_ids: ["ev-1"],
  contradicting_evidence_ids: [],
};

describe("HypothesisPanel", () => {
  it("shows a placeholder when there are no hypotheses yet", () => {
    render(<HypothesisPanel hypotheses={[]} />);
    expect(screen.getByText("No hypotheses yet.")).toBeInTheDocument();
  });

  it("renders a hypothesis's status, confidence, and statement", () => {
    render(<HypothesisPanel hypotheses={[HYPOTHESIS]} />);

    expect(screen.getByTestId("hypothesis-status")).toHaveTextContent(
      "supported",
    );
    expect(screen.getByText("confidence: high")).toBeInTheDocument();
    expect(
      screen.getByText("The change is primarily driven by order_volume."),
    ).toBeInTheDocument();
  });

  it("omits the confidence label when confidence is null", () => {
    render(
      <HypothesisPanel hypotheses={[{ ...HYPOTHESIS, confidence: null }]} />,
    );
    expect(screen.queryByText(/confidence:/)).not.toBeInTheDocument();
  });
});
