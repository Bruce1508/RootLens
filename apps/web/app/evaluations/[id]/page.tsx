import fs from "node:fs";
import path from "node:path";
import { EvaluationView } from "./evaluation-view";

export function generateStaticParams() {
  if (!process.env.NEXT_PUBLIC_DEMO_MODE) return [];
  const idsPath = path.join(process.cwd(), "public/demo/evaluation-ids.json");
  const ids = JSON.parse(fs.readFileSync(idsPath, "utf-8")) as string[];
  return ids.map((id) => ({ id }));
}

export default async function EvaluationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <EvaluationView id={id} />;
}
