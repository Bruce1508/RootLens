import type { HypothesisPayload } from "@/lib/api-client";

const STATUS_STYLES: Record<HypothesisPayload["status"], string> = {
  untested: "text-faint",
  testing: "text-active",
  supported: "text-positive",
  rejected: "text-negative",
  inconclusive: "text-caution",
};

interface HypothesisPanelProps {
  hypotheses: HypothesisPayload[];
}

export function HypothesisPanel({ hypotheses }: HypothesisPanelProps) {
  if (hypotheses.length === 0) {
    return <p className="text-sm text-faint">No hypotheses yet.</p>;
  }

  return (
    <ul className="space-y-3">
      {hypotheses.map((hypothesis) => (
        <li key={hypothesis.id} className="rounded border border-line bg-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <span
              data-testid="hypothesis-status"
              className={`font-mono text-xs font-medium tracking-wider uppercase ${STATUS_STYLES[hypothesis.status]}`}
            >
              {hypothesis.status}
            </span>
            {hypothesis.confidence && (
              <span className="font-mono text-xs text-faint">
                confidence: {hypothesis.confidence}
              </span>
            )}
          </div>
          <p className="mt-2.5 text-sm leading-relaxed text-ink">{hypothesis.statement}</p>
        </li>
      ))}
    </ul>
  );
}
