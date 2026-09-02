interface KpiCardProps {
  label: string;
  currentValue: string;
  percentChange: string;
  isNegative: boolean;
}

export function KpiCard({ label, currentValue, percentChange, isNegative }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <p className="text-sm text-neutral-500 dark:text-neutral-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{currentValue}</p>
      <p
        data-testid="kpi-change"
        data-direction={isNegative ? "down" : "up"}
        className={
          isNegative
            ? "mt-1 text-sm text-red-600 dark:text-red-400"
            : "mt-1 text-sm text-green-600 dark:text-green-400"
        }
      >
        {percentChange}
      </p>
    </div>
  );
}
