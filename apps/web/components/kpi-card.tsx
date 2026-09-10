interface KpiCardProps {
  label: string;
  currentValue: string;
  percentChange: string;
  isNegative: boolean;
}

export function KpiCard({ label, currentValue, percentChange, isNegative }: KpiCardProps) {
  return (
    <div className="border-l-2 border-line-strong pl-4">
      <p className="eyebrow">{label}</p>
      <p className="mt-2 font-mono text-3xl font-medium tracking-tight tabular-nums">
        {currentValue}
      </p>
      <p
        data-testid="kpi-change"
        data-direction={isNegative ? "down" : "up"}
        className={`mt-1.5 flex items-baseline gap-1.5 font-mono text-sm tabular-nums ${
          isNegative ? "text-negative" : "text-positive"
        }`}
      >
        {/* The arrow is a sibling of the value, never part of its text node:
            the percentage element has to read as exactly the formatted
            string so the KPI tests can match it. */}
        <span aria-hidden="true">{isNegative ? "▼" : "▲"}</span>
        <span>{percentChange}</span>
      </p>
    </div>
  );
}
