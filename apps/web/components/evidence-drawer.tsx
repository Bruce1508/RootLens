import type { EvidenceView } from "@/lib/api-client";

interface EvidenceDrawerProps {
  evidence: EvidenceView | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}

export function EvidenceDrawer({ evidence, isLoading, error, onClose }: EvidenceDrawerProps) {
  return (
    <>
      <button
        type="button"
        aria-label="Close evidence detail"
        onClick={onClose}
        className="fixed inset-0 z-10 cursor-default bg-bg/70"
      />
      <div
        role="dialog"
        aria-label="Evidence detail"
        className="fixed inset-y-0 right-0 z-20 flex w-full max-w-xl flex-col border-l border-line-strong bg-surface"
      >
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 className="eyebrow">Evidence</h2>
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-xs text-muted transition-colors hover:text-ink"
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {isLoading && <p className="font-mono text-xs text-faint">Loading…</p>}
          {error && (
            <p className="text-sm text-negative" role="alert">
              {error}
            </p>
          )}

          {evidence && !isLoading && !error && (
            <div className="space-y-6">
              <div>
                <p className="eyebrow">Tool</p>
                <p className="mt-1.5 font-mono text-sm text-signal">{evidence.tool_name}</p>
              </div>

              <div>
                <p className="eyebrow">Executed query</p>
                <pre className="mt-1.5 overflow-x-auto rounded border border-line bg-bg p-3 font-mono text-xs leading-relaxed text-ink">
                  {evidence.sql}
                </pre>
              </div>

              <div className="flex gap-5 font-mono text-xs text-faint tabular-nums">
                <span>{evidence.row_count} rows</span>
                <span>{evidence.execution_ms.toFixed(1)} ms</span>
              </div>

              {evidence.warnings.length > 0 && (
                <ul className="space-y-1 font-mono text-xs text-caution">
                  {evidence.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}

              <div className="overflow-x-auto">
                <table className="w-full border-collapse font-mono text-xs">
                  <thead>
                    <tr>
                      {evidence.columns.map((column) => (
                        <th
                          key={column}
                          className="border-b border-line-strong px-2 py-2 text-left font-medium tracking-wider text-faint uppercase"
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evidence.rows.map((row, index) => (
                      // Evidence rows have no stable id of their own — index is
                      // fine since this table is a static snapshot, never reordered.

                      <tr key={index}>
                        {evidence.columns.map((column) => (
                          <td
                            key={column}
                            className="border-b border-line px-2 py-1.5 text-muted tabular-nums"
                          >
                            {String(row[column] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
