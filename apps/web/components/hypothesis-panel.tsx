import type { HypothesisPayload } from "@/lib/api-client";

const STATUS_STYLES: Record<HypothesisPayload["status"], string> = {
  untested:
    "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
  testing: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  supported:
    "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
  rejected: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  inconclusive:
    "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

interface HypothesisPanelProps {
  hypotheses: HypothesisPayload[];
}

export function HypothesisPanel({ hypotheses }: HypothesisPanelProps) {
  if (hypotheses.length === 0) {
    return (
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        No hypotheses yet.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {hypotheses.map((hypothesis) => (
        <li
          key={hypothesis.id}
          className="rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
        >
          <div className="flex items-center justify-between gap-2">
            <span
              data-testid="hypothesis-status"
              className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[hypothesis.status]}`}
            >
              {hypothesis.status}
            </span>
            {hypothesis.confidence && (
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                confidence: {hypothesis.confidence}
              </span>
            )}
          </div>
          <p className="mt-2 text-neutral-700 dark:text-neutral-300">
            {hypothesis.statement}
          </p>
        </li>
      ))}
    </ul>
  );
}
