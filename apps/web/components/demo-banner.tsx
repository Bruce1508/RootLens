import fs from "node:fs";
import path from "node:path";

export function DemoBanner() {
  const metaPath = path.join(process.cwd(), "public/demo/captured-at.json");
  const { captured_at: capturedAt } = JSON.parse(fs.readFileSync(metaPath, "utf-8")) as {
    captured_at: string;
  };

  return (
    <div className="border-b border-line bg-surface px-6 py-2 text-center font-mono text-xs text-muted">
      Read-only demo — investigations captured {capturedAt}. The investigation
      loop needs a local LLM, so this replays real runs instead of computing
      new ones.
    </div>
  );
}
