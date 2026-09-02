import { describe, expect, it } from "vitest";
import { formatCurrency, formatPercentChange } from "@/lib/format";

describe("formatCurrency", () => {
  it("formats a positive value with two decimals", () => {
    expect(formatCurrency(150)).toBe("$150.00");
  });

  it("formats a value with cents", () => {
    expect(formatCurrency(83.333333)).toBe("$83.33");
  });
});

describe("formatPercentChange", () => {
  it("formats a negative change with a minus sign", () => {
    expect(formatPercentChange(-0.4)).toBe("-40.0%");
  });

  it("formats a positive change with a plus sign", () => {
    expect(formatPercentChange(0.1)).toBe("+10.0%");
  });

  it("returns a placeholder when the comparison value was zero", () => {
    expect(formatPercentChange(null)).toBe("—");
  });
});
