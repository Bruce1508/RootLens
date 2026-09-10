// Grouped thousands, always two decimals: revenue figures on the real
// dataset run to seven digits, where an ungrouped "$945606.29" is
// genuinely hard to read at a glance.
const CURRENCY_FORMAT = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatCurrency(value: number): string {
  return `$${CURRENCY_FORMAT.format(value)}`;
}

export function formatPercentChange(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value * 100).toFixed(1)}%`;
}
