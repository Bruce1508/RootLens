export function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function formatPercentChange(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value * 100).toFixed(1)}%`;
}
