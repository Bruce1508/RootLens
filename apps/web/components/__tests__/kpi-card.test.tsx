import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KpiCard } from "@/components/kpi-card";

describe("KpiCard", () => {
  it("renders the label, current value, and percent change", () => {
    render(
      <KpiCard
        label="Product revenue"
        currentValue="$150.00"
        percentChange="-40.0%"
        isNegative
      />,
    );

    expect(screen.getByText("Product revenue")).toBeInTheDocument();
    expect(screen.getByText("$150.00")).toBeInTheDocument();
    expect(screen.getByText("-40.0%")).toBeInTheDocument();
  });

  it("marks a negative change with a data attribute for styling", () => {
    render(
      <KpiCard label="Orders" currentValue="2" percentChange="-33.3%" isNegative />,
    );

    expect(screen.getByTestId("kpi-change")).toHaveAttribute("data-direction", "down");
  });

  it("marks a positive change with a data attribute for styling", () => {
    render(
      <KpiCard label="Orders" currentValue="4" percentChange="+10.0%" isNegative={false} />,
    );

    expect(screen.getByTestId("kpi-change")).toHaveAttribute("data-direction", "up");
  });
});
