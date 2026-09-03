import type { EvidenceView } from "@/lib/api-client";

interface EvidenceDrawerProps {
  evidence: EvidenceView | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}

export function EvidenceDrawer({
  evidence,
  isLoading,
  error,
  onClose,
}: EvidenceDrawerProps) {
  return (
    <div
      role="dialog"
      aria-label="Evidence detail"
      className="fixed inset-y-0 right-0 z-10 w-full max-w-lg overflow-y-auto border-l border-neutral-200 bg-white p-6 shadow-lg dark:border-neutral-800 dark:bg-neutral-950"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Evidence</h2>
        <button
          type="button"
          onClick={onClose}
          className="rounded px-2 py-1 text-sm text-neutral-500 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"
        >
          Close
        </button>
      </div>

      {isLoading && <p className="mt-4 text-sm text-neutral-500">Loading…</p>}
      {error && (
        <p className="mt-4 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      {evidence && !isLoading && !error && (
        <div className="mt-4 space-y-4 text-sm">
          <div>
            <p className="text-neutral-500 dark:text-neutral-400">Tool</p>
            <p className="font-mono">{evidence.tool_name}</p>
          </div>

          <div>
            <p className="text-neutral-500 dark:text-neutral-400">
              SQL / computation
            </p>
            <pre className="mt-1 overflow-x-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-900">
              {evidence.sql}
            </pre>
          </div>

          <div className="flex gap-4 text-xs text-neutral-500 dark:text-neutral-400">
            <span>{evidence.row_count} rows</span>
            <span>{evidence.execution_ms.toFixed(1)} ms</span>
          </div>

          {evidence.warnings.length > 0 && (
            <ul className="list-inside list-disc text-xs text-amber-700 dark:text-amber-400">
              {evidence.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr>
                  {evidence.columns.map((column) => (
                    <th
                      key={column}
                      className="border-b border-neutral-200 px-2 py-1 text-left font-medium dark:border-neutral-800"
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
                        className="border-b border-neutral-100 px-2 py-1 dark:border-neutral-900"
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
  );
}
