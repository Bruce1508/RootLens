export interface Exhibit {
  evidenceId: string;
  ordinal: number;
  toolName: string;
  rowCount: number;
  executionMs: number;
}

interface EvidenceLedgerProps {
  exhibits: Exhibit[];
  /** Evidence id currently hovered from a report citation, if any — the
      ledger highlights the matching exhibit so a claim and the query
      behind it are visibly the same object. */
  linkedEvidenceId: string | null;
  onHoverExhibit: (evidenceId: string | null) => void;
  onOpenExhibit: (evidenceId: string) => void;
}

export function EvidenceLedger({
  exhibits,
  linkedEvidenceId,
  onHoverExhibit,
  onOpenExhibit,
}: EvidenceLedgerProps) {
  return (
    <div className="rounded border border-line bg-surface">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-3">
        <h2 className="eyebrow">Evidence ledger</h2>
        <span className="font-mono text-xs text-faint tabular-nums">{exhibits.length}</span>
      </div>

      {exhibits.length === 0 ? (
        <p className="px-4 py-4 font-mono text-xs text-faint">
          No queries executed yet.
        </p>
      ) : (
        <ul>
          {exhibits.map((exhibit) => {
            const isLinked = exhibit.evidenceId === linkedEvidenceId;
            return (
              <li key={exhibit.evidenceId} className="exhibit-enter border-b border-line last:border-0">
                <button
                  type="button"
                  onClick={() => onOpenExhibit(exhibit.evidenceId)}
                  onMouseEnter={() => onHoverExhibit(exhibit.evidenceId)}
                  onMouseLeave={() => onHoverExhibit(null)}
                  onFocus={() => onHoverExhibit(exhibit.evidenceId)}
                  onBlur={() => onHoverExhibit(null)}
                  className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors ${
                    isLinked ? "bg-raised" : "hover:bg-raised"
                  }`}
                >
                  <span
                    className={`font-mono text-xs font-medium tabular-nums transition-colors ${
                      isLinked ? "text-signal" : "text-faint"
                    }`}
                  >
                    E{exhibit.ordinal}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-mono text-xs text-ink">
                      {exhibit.toolName}
                    </span>
                    <span className="mt-1 block font-mono text-xs text-faint tabular-nums">
                      {exhibit.rowCount} {exhibit.rowCount === 1 ? "row" : "rows"} ·{" "}
                      {exhibit.executionMs.toFixed(1)} ms
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
